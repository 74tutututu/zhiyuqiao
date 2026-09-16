(function (root, factory) {
  var api = factory();

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
  if (typeof window !== 'undefined') {
    window.ZhiYuQiaoAssistantState = api;
  }
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var MAX_HISTORY_MESSAGES = 20;
  var MAX_MESSAGE_LENGTH = 12000;

  function copyMessage(message) {
    return { role: message.role, content: message.content };
  }

  function copyHistory(history) {
    var messages = Array.isArray(history) ? history : [];
    return messages.slice(-MAX_HISTORY_MESSAGES).map(copyMessage);
  }

  function normalizeText(text) {
    if (typeof text !== 'string') {
      return null;
    }

    text = text.trim();
    if (!text || text.length > MAX_MESSAGE_LENGTH) {
      return null;
    }

    return text;
  }

  function createAssistantStateController(options) {
    options = options || {};

    var historyStore = options.historyStore;
    var selectedSkill = typeof options.selectedSkill === 'string' ? options.selectedSkill : '';
    var topic = typeof options.topic === 'string' ? options.topic : undefined;
    var inputPrefill = typeof options.inputPrefill === 'string' ? options.inputPrefill : '';
    var pendingUserMessage = null;
    var pendingSkill = null;

    function getHistory(skillKey) {
      if (!historyStore || typeof historyStore.getHistory !== 'function') {
        return [];
      }
      return copyHistory(historyStore.getHistory(skillKey));
    }

    function trimForPendingTurn(skillKey) {
      var history = getHistory(skillKey);
      var index;

      if (history.length <= MAX_HISTORY_MESSAGES - 2) {
        return true;
      }
      if (!historyStore || typeof historyStore.clear !== 'function' || typeof historyStore.appendTurn !== 'function') {
        return false;
      }

      history = history.slice(-(MAX_HISTORY_MESSAGES - 2));
      if (historyStore.clear(skillKey) !== true) {
        return false;
      }

      for (index = 0; index + 1 < history.length; index += 2) {
        if (historyStore.appendTurn(skillKey, history[index].content, history[index + 1].content) !== true) {
          return false;
        }
      }
      return true;
    }

    function selectSkill(skillKey, options, includePrompt) {
      options = options || {};
      if (options.loading) {
        return false;
      }

      selectedSkill = skillKey;
      if (typeof options.topic === 'string') {
        topic = options.topic;
      }
      if (includePrompt && typeof options.prompt === 'string') {
        inputPrefill = options.prompt;
      }
      return true;
    }

    function recordUserMessage(text) {
      text = normalizeText(text);
      if (!text || pendingUserMessage !== null || !trimForPendingTurn(selectedSkill)) {
        return false;
      }

      pendingUserMessage = text;
      pendingSkill = selectedSkill;
      return true;
    }

    function recordAssistantReply(reply) {
      var userMessage = pendingUserMessage;
      var skillKey = pendingSkill;

      if (!userMessage || !historyStore || typeof historyStore.appendTurn !== 'function') {
        return false;
      }
      if (historyStore.appendTurn(skillKey, userMessage, reply) !== true) {
        return false;
      }

      pendingUserMessage = null;
      pendingSkill = null;
      return true;
    }

    return {
      selectFromSidebar: function (skillKey, selectionOptions) {
        return selectSkill(skillKey, selectionOptions, false);
      },
      selectFromShortcut: function (skillKey, selectionOptions) {
        return selectSkill(skillKey, selectionOptions, true);
      },
      recordUserMessage: recordUserMessage,
      buildRequestPayload: function () {
        var skillKey = pendingSkill || selectedSkill;
        var history = getHistory(skillKey);

        if (pendingUserMessage !== null) {
          history.push({ role: 'user', content: pendingUserMessage });
        }

        return {
          skill_key: skillKey,
          history: history.slice(-MAX_HISTORY_MESSAGES)
        };
      },
      recordAssistantCompletion: function (reply) {
        reply = normalizeText(reply) || '暂时无法完成，请重试。';
        return recordAssistantReply(reply);
      },
      recordAssistantStop: function (partialReply, stoppedLabel) {
        var label = normalizeText(stoppedLabel) || '已停止生成';
        var partial = normalizeText(partialReply);
        var reply = partial ? partial + '\n\n---\n' + label : label;

        return recordAssistantReply(reply);
      },
      clearCurrentHistory: function () {
        var cleared;

        if (!historyStore || typeof historyStore.clear !== 'function') {
          return false;
        }
        cleared = historyStore.clear(selectedSkill);
        if (cleared && pendingSkill === selectedSkill) {
          pendingUserMessage = null;
          pendingSkill = null;
        }
        return cleared;
      },
      snapshot: function () {
        return {
          selectedSkill: selectedSkill,
          topic: topic,
          inputPrefill: inputPrefill,
          history: getHistory(selectedSkill)
        };
      }
    };
  }

  return { createAssistantStateController: createAssistantStateController };
}));
