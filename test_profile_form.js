const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function field(value, checked = false) {
    return { value, checked, handlers: {}, addEventListener(event, handler) { this.handlers[event] = handler; } };
}
const languages = [field('中文', true), field('English'), field('Français')];
const primary = field('中文');
primary.options = languages.map(item => ({ value: item.value, disabled: false }));
const form = {
    handlers: {},
    querySelectorAll(selector) { return selector.includes('teaching_languages') ? languages : []; },
    querySelector() { return primary; },
    addEventListener(event, handler) { this.handlers[event] = handler; },
};
vm.runInNewContext(fs.readFileSync('static/profile-form.js', 'utf8'), {
    document: { querySelector() { return form; } },
});
assert.ok(primary.options.every(option => !option.disabled), 'All languages must remain selectable');
primary.value = 'English';
primary.handlers.change();
assert.equal(languages[1].checked, true, 'Selecting English must also check its language chip');
assert.equal(languages[0].checked, true, 'Existing language choices must be preserved');
languages[1].checked = false;
languages[1].handlers.change();
assert.equal(primary.value, '中文', 'Removing the primary language selects another checked language');
languages[0].checked = false;
languages[0].handlers.change();
assert.equal(languages[0].checked, true, 'Keep at least the primary language selected');
primary.value = 'Français';
form.handlers.submit();
assert.equal(languages[2].checked, true, 'Submission must include the primary language');
assert.ok(primary.options.every(option => !option.disabled));
console.log('[OK] profile dropdown selection, checkbox sync and submission regressions passed');
