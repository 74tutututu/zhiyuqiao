(function (root, factory) {
  var api = factory();

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
  if (typeof window !== 'undefined') {
    window.ZhiYuQiaoChatHistory = api;
  }
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var MAX_MESSAGE_LENGTH = 12000;
  var MAX_MESSAGES_PER_TOOL = 20;

  function isValidMessage(message, role) {
    return message &&
      message.role === role &&
      typeof message.content === 'string' &&
      message.content.trim().length > 0 &&
      message.content.trim().length <= MAX_MESSAGE_LENGTH;
  }

  function copyMessage(message) {
    return { role: message.role, content: message.content };
  }

  function normalizeHistory(messages) {
    var normalized = [];
    var index;

    if (!Array.isArray(messages)) {
      return normalized;
    }

    for (index = 0; index + 1 < messages.length && normalized.length < MAX_MESSAGES_PER_TOOL; index += 2) {
      if (isValidMessage(messages[index], 'user') && isValidMessage(messages[index + 1], 'assistant')) {
        normalized.push(copyMessage(messages[index]), copyMessage(messages[index + 1]));
      }
    }

    return normalized;
  }

  function createHistoryStore(options) {
    options = options || {};

    var storage = options.storage;
    var storageKey = options.storageKey;
    var allowedKeys = Object.create(null);
    var histories = Object.create(null);
    var skillKeys = Array.isArray(options.skillKeys) ? options.skillKeys : [];
    var loaded = {};
    var raw;
    var index;

    for (index = 0; index < skillKeys.length; index += 1) {
      if (typeof skillKeys[index] === 'string' && skillKeys[index].length > 0) {
        allowedKeys[skillKeys[index]] = true;
        histories[skillKeys[index]] = [];
      }
    }

    try {
      raw = storage && typeof storage.getItem === 'function' ? storage.getItem(storageKey) : null;
      if (typeof raw === 'string') {
        loaded = JSON.parse(raw);
      }
    } catch (error) {
      loaded = {};
    }

    if (loaded && typeof loaded === 'object' && !Array.isArray(loaded)) {
      Object.keys(allowedKeys).forEach(function (key) {
        histories[key] = normalizeHistory(loaded[key]);
      });
    }

    function persist() {
      var serialized = {};

      Object.keys(allowedKeys).forEach(function (key) {
        serialized[key] = histories[key].map(copyMessage);
      });

      try {
        if (storage && typeof storage.setItem === 'function') {
          storage.setItem(storageKey, JSON.stringify(serialized));
          return true;
        }
      } catch (error) {
        return false;
      }

      return false;
    }

    return {
      getHistory: function (skillKey) {
        if (!allowedKeys[skillKey]) {
          return [];
        }
        return histories[skillKey].map(copyMessage);
      },
      appendTurn: function (skillKey, userMessage, assistantMessage) {
        if (!allowedKeys[skillKey] || !isValidMessage(userMessage, 'user') || !isValidMessage(assistantMessage, 'assistant')) {
          return false;
        }

        while (histories[skillKey].length + 2 > MAX_MESSAGES_PER_TOOL) {
          histories[skillKey].splice(0, 2);
        }
        histories[skillKey].push(copyMessage(userMessage), copyMessage(assistantMessage));
        persist();
        return true;
      },
      clear: function (skillKey) {
        if (!allowedKeys[skillKey]) {
          return false;
        }

        histories[skillKey] = [];
        persist();
        return true;
      },
      persist: persist
    };
  }

  return { createHistoryStore: createHistoryStore };
}));
