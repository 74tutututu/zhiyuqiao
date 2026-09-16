'use strict';

const assert = require('assert');
const { createHistoryStore } = require('./static/chat_history');
const { createAssistantStateController } = require('./static/assistant_state');

function createMemoryStorage(initial) {
  const data = Object.assign(Object.create(null), initial);
  return {
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(data, key) ? data[key] : null;
    },
    setItem(key, value) {
      data[key] = String(value);
    }
  };
}

function message(role, content) {
  return { role, content };
}

function append(store, skillKey, label) {
  assert.strictEqual(store.appendTurn(skillKey, 'question ' + label, 'answer ' + label), true);
}

function createStore(storage) {
  return createHistoryStore({
    storage,
    storageKey: 'assistant-history',
    skillKeys: ['tool-a', 'tool-b']
  });
}

function test(name, fn) {
  try {
    fn();
    console.log('PASS ' + name);
  } catch (error) {
    console.error('FAIL ' + name);
    throw error;
  }
}

test('evicts the oldest complete turn before the eleventh request', () => {
  const store = createStore(createMemoryStorage());
  const controller = createAssistantStateController({ historyStore: store, selectedSkill: 'tool-a' });
  let index;

  for (index = 1; index <= 10; index += 1) {
    append(store, 'tool-a', String(index));
  }

  assert.strictEqual(controller.recordUserMessage('question 11'), true);
  const payload = controller.buildRequestPayload();

  assert.deepStrictEqual(Object.keys(payload).sort(), ['history', 'skill_key']);
  assert.strictEqual(payload.skill_key, 'tool-a');
  assert.ok(payload.history.length <= 20);
  assert.deepStrictEqual(payload.history[0], message('user', 'question 2'));
  assert.deepStrictEqual(payload.history[payload.history.length - 1], message('user', 'question 11'));
  assert.strictEqual(controller.recordAssistantCompletion('answer 11'), true);
  assert.strictEqual(store.getHistory('tool-a').length, 20);
});

test('blocks both skill-selection entry points without changing state while loading', () => {
  const controller = createAssistantStateController({ historyStore: createStore(createMemoryStorage()), selectedSkill: 'tool-a' });

  assert.strictEqual(controller.selectFromShortcut('tool-a', {
    loading: false,
    topic: '初始主题',
    prompt: '原始预填'
  }), true);
  const before = controller.snapshot();

  assert.strictEqual(controller.selectFromSidebar('tool-b', { loading: true, topic: '侧栏主题' }), false);
  assert.deepStrictEqual(controller.snapshot(), before);
  assert.strictEqual(controller.selectFromShortcut('tool-b', {
    loading: true,
    topic: '快捷主题',
    prompt: '新的预填'
  }), false);
  assert.deepStrictEqual(controller.snapshot(), before);

  assert.strictEqual(controller.selectFromSidebar('tool-b', { loading: false, topic: '侧栏主题' }), true);
  assert.strictEqual(controller.snapshot().selectedSkill, 'tool-b');
  assert.strictEqual(controller.snapshot().topic, '侧栏主题');
  assert.strictEqual(controller.snapshot().inputPrefill, '原始预填');
  assert.strictEqual(controller.selectFromShortcut('tool-a', {
    loading: false,
    topic: '快捷主题',
    prompt: '新的预填'
  }), true);
  assert.strictEqual(controller.snapshot().inputPrefill, '新的预填');
});

test('persists stopped replies as complete user-assistant turns and restores them', () => {
  const storage = createMemoryStorage();
  const firstStore = createStore(storage);
  const first = createAssistantStateController({ historyStore: firstStore, selectedSkill: 'tool-a' });

  assert.strictEqual(first.recordUserMessage('请继续'), true);
  assert.strictEqual(first.recordAssistantStop('部分回答', '已停止生成'), true);
  assert.deepStrictEqual(firstStore.getHistory('tool-a'), [
    message('user', '请继续'),
    message('assistant', '部分回答\n\n---\n已停止生成')
  ]);

  const restoredStore = createStore(storage);
  const restored = createAssistantStateController({ historyStore: restoredStore, selectedSkill: 'tool-a' });
  assert.deepStrictEqual(restored.snapshot().history, firstStore.getHistory('tool-a'));

  assert.strictEqual(restored.recordUserMessage('空回复'), true);
  assert.strictEqual(restored.recordAssistantStop('', '已停止生成'), true);
  assert.deepStrictEqual(restoredStore.getHistory('tool-a').slice(-2), [
    message('user', '空回复'),
    message('assistant', '已停止生成')
  ]);
});

test('closes pending turns with a valid fallback when completion replies are invalid', () => {
  const invalidReplies = ['', null, 'x'.repeat(12001)];

  invalidReplies.forEach((reply, index) => {
    const store = createStore(createMemoryStorage());
    const controller = createAssistantStateController({ historyStore: store, selectedSkill: 'tool-a' });
    const question = '无效回复问题 ' + index;

    assert.strictEqual(controller.recordUserMessage(question), true);
    assert.strictEqual(controller.recordAssistantCompletion(reply), true);
    assert.deepStrictEqual(store.getHistory('tool-a'), [
      message('user', question),
      message('assistant', '暂时无法完成，请重试。')
    ]);
  });
});

test('keeps tool histories isolated when controllers switch tools', () => {
  const store = createStore(createMemoryStorage());
  const toolA = createAssistantStateController({ historyStore: store, selectedSkill: 'tool-a' });
  const toolB = createAssistantStateController({ historyStore: store, selectedSkill: 'tool-b' });

  assert.strictEqual(toolA.recordUserMessage('A 问题'), true);
  assert.strictEqual(toolA.recordAssistantCompletion('A 回答'), true);
  assert.strictEqual(toolB.recordUserMessage('B 问题'), true);
  assert.strictEqual(toolB.recordAssistantCompletion('B 回答'), true);

  assert.deepStrictEqual(toolA.snapshot().history, [message('user', 'A 问题'), message('assistant', 'A 回答')]);
  assert.deepStrictEqual(toolB.snapshot().history, [message('user', 'B 问题'), message('assistant', 'B 回答')]);
  assert.strictEqual(toolA.selectFromSidebar('tool-b', { loading: false, topic: 'B' }), true);
  assert.deepStrictEqual(toolA.snapshot().history, toolB.snapshot().history);
});

test('clears only the current tool history', () => {
  const store = createStore(createMemoryStorage());
  append(store, 'tool-a', 'A');
  append(store, 'tool-b', 'B');
  const controller = createAssistantStateController({ historyStore: store, selectedSkill: 'tool-a' });

  assert.strictEqual(controller.clearCurrentHistory(), true);
  assert.deepStrictEqual(store.getHistory('tool-a'), []);
  assert.deepStrictEqual(store.getHistory('tool-b'), [message('user', 'question B'), message('assistant', 'answer B')]);
});

console.log('All assistant state controller tests passed.');
