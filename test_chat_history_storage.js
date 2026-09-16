'use strict';

const assert = require('assert');
const { createHistoryStore } = require('./static/chat_history');

function createMemoryStorage(initial) {
  const data = Object.assign(Object.create(null), initial);
  return {
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(data, key) ? data[key] : null;
    },
    setItem(key, value) {
      data[key] = String(value);
    },
    dump(key) {
      return data[key];
    }
  };
}

function message(role, content) {
  return { role, content };
}

function append(store, toolKey, label) {
  return store.appendTurn(
    toolKey,
    'question ' + label,
    'answer ' + label
  );
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

test('keeps histories isolated by tool key', () => {
  const storage = createMemoryStorage();
  const store = createHistoryStore({ storage, storageKey: 'history', skillKeys: ['tool-a', 'tool-b'] });

  append(store, 'tool-a', 'A');
  append(store, 'tool-b', 'B');

  assert.deepStrictEqual(store.getHistory('tool-a'), [message('user', 'question A'), message('assistant', 'answer A')]);
  assert.deepStrictEqual(store.getHistory('tool-b'), [message('user', 'question B'), message('assistant', 'answer B')]);
});

test('restores persisted histories after rebuilding the store', () => {
  const storage = createMemoryStorage();
  const first = createHistoryStore({ storage, storageKey: 'history', skillKeys: ['tool-a'] });
  append(first, 'tool-a', 'saved');
  first.persist();

  const restored = createHistoryStore({ storage, storageKey: 'history', skillKeys: ['tool-a'] });

  assert.deepStrictEqual(restored.getHistory('tool-a'), [message('user', 'question saved'), message('assistant', 'answer saved')]);
});

test('ignores invalid JSON, unknown tools, and invalid messages', () => {
  const badJsonStorage = createMemoryStorage({ history: '{not json' });
  const badJsonStore = createHistoryStore({ storage: badJsonStorage, storageKey: 'history', skillKeys: ['tool-a'] });
  assert.deepStrictEqual(badJsonStore.getHistory('tool-a'), []);

  const storage = createMemoryStorage({
    history: JSON.stringify({
      'tool-a': [
        message('user', 'valid'),
        message('assistant', 'reply'),
        message('user', '   '),
        message('assistant', 'ignored'),
        message('tool', 'invalid role'),
        message('assistant', 'ignored too')
      ],
      unknown: [message('user', 'not loaded'), message('assistant', 'not loaded')]
    })
  });
  const store = createHistoryStore({ storage, storageKey: 'history', skillKeys: ['tool-a'] });

  assert.deepStrictEqual(store.getHistory('tool-a'), [message('user', 'valid'), message('assistant', 'reply')]);
  assert.deepStrictEqual(store.getHistory('unknown'), []);
  assert.strictEqual(store.appendTurn('tool-a', 'x', ' '.repeat(12001)), false);
  assert.deepStrictEqual(store.getHistory('tool-a'), [message('user', 'valid'), message('assistant', 'reply')]);
});

test('evicts the earliest complete turn when appending the eleventh turn', () => {
  const store = createHistoryStore({ storage: createMemoryStorage(), storageKey: 'history', skillKeys: ['tool-a'] });
  for (let index = 1; index <= 11; index += 1) {
    append(store, 'tool-a', String(index));
  }

  const history = store.getHistory('tool-a');
  assert.strictEqual(history.length, 20);
  assert.deepStrictEqual(history[0], message('user', 'question 2'));
  assert.deepStrictEqual(history[1], message('assistant', 'answer 2'));
  assert.deepStrictEqual(history[18], message('user', 'question 11'));
  assert.deepStrictEqual(history[19], message('assistant', 'answer 11'));
});

test('clears only the selected tool history', () => {
  const store = createHistoryStore({ storage: createMemoryStorage(), storageKey: 'history', skillKeys: ['tool-a', 'tool-b'] });
  append(store, 'tool-a', 'A');
  append(store, 'tool-b', 'B');

  assert.strictEqual(store.clear('tool-a'), true);
  assert.deepStrictEqual(store.getHistory('tool-a'), []);
  assert.deepStrictEqual(store.getHistory('tool-b'), [message('user', 'question B'), message('assistant', 'answer B')]);
});

console.log('All chat history storage tests passed.');
