/* Welcome dashboard rendered when no messages are present.
 * RICH business-oriented variant — only depends on _esc from util.js. */

Object.assign(ChatApp.prototype, {

  _showWelcome() {
    const el = document.getElementById('messages');
    el.innerHTML = '<div style="flex:1"></div>';
    const dash = document.createElement('div');
    dash.style.cssText = 'max-width:680px;margin:0 auto;padding:20px 0;';
    dash.innerHTML = `
      <div style="text-align:center;margin-bottom:20px;">
        <div style="font-size:28px;font-weight:700;color:var(--accent);margin-bottom:4px;">RICH 智能助手</div>
        <div style="font-size:13px;color:var(--text-muted);">财富管理业务助手 &bull; 页面导航 &bull; 任务/工作流确认执行</div>
      </div>

      ${this._dashSection('常用问题', [
        this._dashCard('查看持仓',        '读取当前用户持仓明细和盈亏',       '我当前持仓怎么样？',         'var(--blue)'),
        this._dashCard('资产配置',        '查看当前权重、目标权重和偏离',     '分析我的资产配置',           'var(--green)'),
        this._dashCard('定投计划',        '查看启用中的定投计划和下次执行日', '查看我的定投计划',           'var(--accent)'),
        this._dashCard('最近交易',        '查看最近买入、卖出和分红记录',     '最近有哪些交易？',           'var(--purple)'),
      ])}

      ${this._dashSection('业务能力', [
        this._dashCard('组合汇总',        '读取总资产、成本、收益和收益率',       '汇总一下我的投资组合',       'var(--blue)'),
        this._dashCard('页面导航',        '按你的描述打开 RICH 系统页面',         '打开系统设置',               'var(--green)'),
        this._dashCard('任务确认',        '需要确认后提交后台原子任务',           '有哪些任务可以执行？',       'var(--accent)'),
        this._dashCard('工作流确认',      '需要确认后启动预设业务流程',           '有哪些工作流？',             'var(--purple)'),
      ])}

      <div style="border:1px solid var(--border);border-radius:var(--radius);background:var(--surface);padding:12px 14px;margin-top:12px;">
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--text-muted);margin-bottom:8px;">安全说明</div>
        <div style="font-size:12px;color:var(--text-muted);line-height:1.7;">
          RICH 模式下，助手只暴露业务白名单工具。它可以读取当前用户的投资组合、持仓、交易和定投计划；不能读取服务器文件、扫描代码仓库或执行终端命令；涉及执行任务或工作流时，会先要求你确认。
        </div>
      </div>
      <div style="text-align:center;margin-top:10px;font-size:11px;color:var(--text-muted);">
        &#9881; 在 RICH 系统设置中配置模型网关 &bull; &#9790; 可切换深浅色主题
      </div>`;
    el.appendChild(dash);
  },

  _dashSection(title, cards) {
    return `<div style="margin-bottom:12px;">
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:.6px;
        color:var(--text-muted);margin-bottom:6px;padding-left:2px;">${title}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">${cards.join('')}</div>
    </div>`;
  },

  _dashCard(title, desc, example, color) {
    return `<div style="background:var(--surface);border:1px solid var(--border);
      border-radius:var(--radius-sm);padding:10px 12px;cursor:pointer;
      border-left:3px solid ${color};transition:background .15s;"
      onmouseenter="this.style.background='var(--panel)'"
      onmouseleave="this.style.background='var(--surface)'"
      onclick="document.getElementById('prompt-input').value='${example}';document.getElementById('prompt-input').focus();">
      <div style="font-size:12px;font-weight:600;color:var(--text);margin-bottom:2px;">${title}</div>
      <div style="font-size:11px;color:var(--text-muted);line-height:1.4;">${desc}</div>
    </div>`;
  },
});
