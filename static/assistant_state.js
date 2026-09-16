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
    var hasDeclaredSkillKeys = Array.isArray(options.skillKeys);
    var declaredSkillKeys = Object.create(null);
    var discoveredSkillKeys = Object.create(null);
    var skillIndex;

    if (hasDeclaredSkillKeys) {
      for (skillIndex = 0; skillIndex < options.skillKeys.length; skillIndex += 1) {
        if (typeof options.skillKeys[skillIndex] === 'string' && options.skillKeys[skillIndex]) {
          declaredSkillKeys[options.skillKeys[skillIndex]] = true;
        }
      }
    }

    function getHistory(skillKey) {
      if (!historyStore || typeof historyStore.getHistory !== 'function') {
        return [];
      }
      return copyHistory(historyStore.getHistory(skillKey));
    }

    function isRegisteredSkill(skillKey) {
      var history;
      var index;
      var probeUser = '__assistant_state_probe_user__';
      var probeAssistant = '__assistant_state_probe_assistant__';

      if (typeof skillKey !== 'string' || !skillKey) {
        return false;
      }
      if (hasDeclaredSkillKeys) {
        return declaredSkillKeys[skillKey] === true;
      }
      if (Object.prototype.hasOwnProperty.call(discoveredSkillKeys, skillKey)) {
        return discoveredSkillKeys[skillKey];
      }
      if (!historyStore || typeof historyStore.appendTurn !== 'function' || typeof historyStore.clear !== 'function') {
        discoveredSkillKeys[skillKey] = false;
        return false;
      }

      history = getHistory(skillKey);
      if (historyStore.appendTurn(skillKey, probeUser, probeAssistant) !== true) {
        discoveredSkillKeys[skillKey] = false;
        return false;
      }
      if (historyStore.clear(skillKey) !== true) {
        discoveredSkillKeys[skillKey] = false;
        return false;
      }
      for (index = 0; index + 1 < history.length; index += 2) {
        if (historyStore.appendTurn(skillKey, history[index].content, history[index + 1].content) !== true) {
          discoveredSkillKeys[skillKey] = false;
          return false;
        }
      }

      discoveredSkillKeys[skillKey] = true;
      return true;
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
      if (options.loading || !isRegisteredSkill(skillKey)) {
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
      if (!text || pendingUserMessage !== null || !isRegisteredSkill(selectedSkill) || !trimForPendingTurn(selectedSkill)) {
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
        var suffix = '\n\n---\n' + label;
        var reply = partial && suffix.length < MAX_MESSAGE_LENGTH
          ? partial.slice(0, MAX_MESSAGE_LENGTH - suffix.length) + suffix
          : label;

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
