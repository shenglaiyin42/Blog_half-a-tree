// 验证所有正式页面接入一次统计，跳转页不接入，本地预览不发送数据。
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const snippet = '<script defer src="/site-analytics.js"></script>';
let count = 0;
function scan(dir) {
  for (const item of fs.readdirSync(dir, {withFileTypes: true})) {
    if (item.name.startsWith('.') || ['node_modules', 'public', 'content'].includes(item.name)) continue;
    const file = path.join(dir, item.name);
    if (item.isDirectory()) { scan(file); continue; }
    if (!file.endsWith('.html')) continue;
    const html = fs.readFileSync(file, 'utf8');
    const redirect = /http-equiv=["']refresh["']/i.test(html);
    assert.equal(html.split(snippet).length - 1, redirect ? 0 : 1, file);
    if (!redirect) count++;
  }
}
scan(root);
const source = fs.readFileSync(path.join(root, 'site-analytics.js'), 'utf8');
for (const hostname of ['halfatree.page', 'www.halfatree.page', 'localhost', '127.0.0.1', '', 'example.com']) {
  const added = [];
  const document = {
    querySelector: () => added.length ? added[0] : null,
    createElement: () => ({setAttribute(key, value) {this[key] = value;}}),
    body: {appendChild: element => added.push(element)},
  };
  const context = vm.createContext({window: {location: {hostname}}, document});
  vm.runInContext(source, context);
  vm.runInContext(source, context);
  const production = ['halfatree.page', 'www.halfatree.page'].includes(hostname);
  assert.equal(added.length, production ? 1 : 0, hostname);
  if (production) {
    assert.equal(added[0].type, 'module');
    assert.equal(added[0].src, 'https://static.cloudflareinsights.com/beacon.min.js');
    assert.match(JSON.parse(added[0]['data-cf-beacon']).token, /^[a-f0-9]{32}$/);
  }
}
console.log(`通过：${count} 个正式页面/模板，跳转页排除，正式域名限制及防重复加载正常。`);
