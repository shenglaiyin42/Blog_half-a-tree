// 访问统计只在正式域名启用；本地预览和直接打开文件不计入。
(() => {
  if (!['halfatree.page', 'www.halfatree.page'].includes(window.location.hostname)) return;
  if (document.querySelector('script[data-cf-beacon]')) return;

  const beacon = document.createElement('script');
  beacon.type = 'module';
  beacon.src = 'https://static.cloudflareinsights.com/beacon.min.js';
  // Cloudflare 提供的公开站点标识，不是账户密钥。
  beacon.setAttribute('data-cf-beacon', JSON.stringify({token: '9994a7cf36fe4ded872aef82187c511b'}));
  document.body.appendChild(beacon);
})();
