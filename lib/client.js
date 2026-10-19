window.__ModuleLoader__.load({
  id: 'dsh-xhs-batch-studio',
  factory: (require) => {
    const React = require('react')
    const h = React.createElement
    const API = '/api/xhs-batch'
    const SETTINGS_KEY = 'xhs-batch-studio.settings.v2'

    const styles = `
      .xhs-root{--ink:#221a1e;--muted:#7b6f76;--line:#ece2e6;--rose:#ff2e55;--rose-soft:#fff0f4;--paper:#fffcfa;
        display:flex;flex-direction:column;height:100%;min-height:0;overflow:hidden;container-type:inline-size;
        background:radial-gradient(120% 80% at 100% 0%,#fff2f5 0%,#fffdfc 42%,#fffdfc 100%);
        color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;box-sizing:border-box}
      .xhs-root *{box-sizing:border-box}
      .xhs-bar{flex:none;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:11px 16px;
        border-bottom:1px solid rgba(236,226,230,.9);background:rgba(255,253,252,.88);backdrop-filter:blur(14px)}
      .xhs-brand{display:flex;align-items:center;gap:10px;min-width:0}
      .xhs-logo{width:32px;height:32px;border-radius:10px;display:grid;place-items:center;background:var(--rose);color:#fff;
        font-size:15px;font-weight:700;box-shadow:0 6px 18px rgba(255,46,85,.24);flex:none}
      .xhs-brand h1{margin:0;font-size:15.5px;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .xhs-brand p{margin:2px 0 0;font-size:11px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .xhs-bar-actions{display:flex;align-items:center;gap:7px;flex:none}
      .xhs-chip{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;padding:4px 9px;border-radius:99px;
        border:1px solid var(--line);background:#fff;color:var(--muted);white-space:nowrap}
      .xhs-chip .dot{width:6px;height:6px;border-radius:50%;background:#c9bfc3}
      .xhs-chip.ok{background:#f2fbf5;border-color:#cfeedd;color:#1c7c4a}.xhs-chip.ok .dot{background:#2eab63}
      .xhs-chip.warn{background:#fff8ec;border-color:#f3e1c2;color:#a8730f}.xhs-chip.warn .dot{background:#e0a020}
      .xhs-btn{border:1px solid var(--line);background:#fff;color:var(--ink);border-radius:9px;padding:7px 11px;
        font:inherit;font-size:12.5px;cursor:pointer;white-space:nowrap;transition:.15s}
      .xhs-btn:hover:not(:disabled){border-color:#dcc7ce;background:#fffafa}
      .xhs-btn:disabled{opacity:.55;cursor:not-allowed}
      .xhs-btn{transition:background .15s,border-color .15s,transform .15s,box-shadow .15s}
      .xhs-btn.primary{background:linear-gradient(135deg,#ff4566,#ff2e55);border-color:transparent;color:#fff;font-weight:600;
        box-shadow:0 7px 16px rgba(255,46,85,.22)}
      .xhs-btn.primary:hover:not(:disabled){background:linear-gradient(135deg,#ff5170,#ff3a5e);border-color:transparent;
        color:#fff;filter:brightness(1.02);transform:translateY(-1px)}
      .xhs-btn.primary:disabled{background:#f4e4e8;border-color:#f0d8de;color:#bd8e9a;box-shadow:none;opacity:1}
      .xhs-btn.ghost{background:transparent;border-color:transparent;color:var(--muted)}
      .xhs-count{display:inline-grid;place-items:center;min-width:16px;height:16px;margin-left:5px;padding:0 4px;border-radius:8px;
        background:var(--rose-soft);color:#c8193b;font-size:10px;font-weight:700}
      .xhs-drawer-overlay{position:fixed;inset:0;z-index:60;background:rgba(23,19,16,.26);display:flex;justify-content:flex-end}
      .xhs-history{width:min(430px,92vw);height:100%;background:#fff;display:flex;flex-direction:column;padding:14px;
        box-shadow:-14px 0 36px rgba(84,42,55,.18);animation:xhs-slide .18s ease-out}
      @keyframes xhs-slide{from{transform:translateX(18px);opacity:.6}to{transform:none;opacity:1}}
      .xhs-history-head{display:flex;align-items:center;gap:8px;margin-bottom:10px}
      .xhs-history-list{flex:1;overflow:auto;display:flex;flex-direction:column;gap:7px;padding-right:2px}
      .xhs-history-row{display:flex;gap:10px;align-items:center;width:100%;border:1px solid var(--line);background:#fff;
        border-radius:12px;padding:8px;text-align:left;font:inherit;cursor:pointer;transition:.15s}
      .xhs-history-row:hover{border-color:#f0c9d3;background:#fffafb;transform:translateX(-2px)}
      .xhs-history-row .thumb{width:44px;height:59px;border-radius:8px;overflow:hidden;background:#f8eef1;display:grid;place-items:center;flex:none}
      .xhs-history-row .thumb img{width:100%;height:100%;object-fit:cover;display:block}
      .xhs-history-row .thumb .ph{font-size:15px;color:#c8193b}
      .xhs-history-row .body{flex:1;min-width:0;display:flex;flex-direction:column;gap:5px}
      .xhs-history-row strong{font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .xhs-history-row .meta{display:flex;align-items:center;gap:6px;font-size:10.5px;color:var(--muted)}
      .xhs-history-row .kind{font-style:normal;border-radius:5px;padding:1px 5px;background:var(--rose-soft);color:#c8193b}
      .xhs-history-row .kind.batch{background:#fff2df;color:#a86400}
      .xhs-history-row .kind.notes{background:#eef3ff;color:#3457a8}
      .xhs-history-row .go{font-size:11px;color:#c8193b;flex:none;opacity:.85}
      .xhs-history-empty{color:var(--muted);font-size:12px;text-align:center;margin-top:60px}
      .xhs-btn.ghost:hover:not(:disabled){background:#f8f1f3;color:var(--ink)}
      .xhs-btn.danger{color:#c8193b;border-color:#f3d2da;background:#fff6f8}
      .xhs-body{flex:1;min-height:0;display:grid;grid-template-columns:326px minmax(0,1fr);gap:11px;padding:11px}
      .xhs-side{min-height:0;overflow:auto;display:flex;flex-direction:column;gap:9px;padding-right:2px}
      .xhs-card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:13px;
        box-shadow:0 6px 20px rgba(84,42,55,.05);transition:box-shadow .18s,border-color .18s}
      .xhs-card:hover{box-shadow:0 10px 26px rgba(84,42,55,.08);border-color:#eedbe1}
      .xhs-card h2{margin:0 0 8px;font-size:13px;display:flex;align-items:center;gap:8px;letter-spacing:.2px}
      .xhs-step{width:19px;height:19px;border-radius:7px;background:var(--rose-soft);color:#c8193b;display:grid;place-items:center;
        font-size:11px;font-weight:700;flex:none;box-shadow:inset 0 0 0 1px rgba(255,46,85,.08)}
      .xhs-card .state{margin-left:auto;font-size:10.5px;color:var(--muted)}
      .xhs-drop{border:1.5px dashed #e7d3da;border-radius:11px;padding:14px 10px;text-align:center;cursor:pointer;
        background:#fffafb;transition:.18s;color:var(--muted);font-size:12px;line-height:1.55}
      .xhs-drop:hover,.xhs-drop.over{border-color:var(--rose);background:var(--rose-soft);color:#c8193b}
      .xhs-drop strong{display:block;font-size:12.5px;color:var(--ink);margin-bottom:2px}
      .xhs-drop.over strong{color:#c8193b}
      .xhs-files{list-style:none;margin:8px 0 0;padding:0;display:flex;flex-direction:column;gap:5px;max-height:150px;overflow:auto}
      .xhs-file{display:flex;align-items:center;gap:7px;padding:5px 7px;border:1px solid var(--line);border-radius:8px;background:#fff;font-size:11.5px;min-width:0}
      .xhs-file .ext{flex:none;width:28px;text-align:center;font-size:9.5px;font-weight:700;color:#c8193b;background:var(--rose-soft);border-radius:4px;padding:3px 0}
      .xhs-file .nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      .xhs-file .sz{flex:none;color:var(--muted);font-size:10.5px}
      .xhs-file button{border:0;background:transparent;color:#b1455d;cursor:pointer;font-size:14px;line-height:1;padding:1px 4px;border-radius:4px}
      .xhs-field{display:grid;gap:4px;margin-bottom:9px}
      .xhs-field:last-child{margin-bottom:0}
      .xhs-label{font-size:11.5px;font-weight:600;display:flex;justify-content:space-between;align-items:center;gap:8px}
      .xhs-hint{font-weight:400;font-size:10.5px;color:var(--muted)}
      .xhs-field input,.xhs-field select,.xhs-field textarea{width:100%;border:1px solid var(--line);border-radius:8px;background:#fff;
        padding:7px 9px;font:inherit;font-size:12.5px;color:var(--ink)}
      .xhs-field textarea{resize:vertical;min-height:52px;line-height:1.55}
      .xhs-field input:focus,.xhs-field select:focus,.xhs-field textarea:focus{outline:2px solid rgba(255,46,85,.16);outline-offset:1px;border-color:#eebcc8}
      .xhs-row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
      .xhs-main{min-width:0;min-height:0;display:flex;flex-direction:column;gap:9px;overflow:hidden}
      .xhs-panel{flex:1;min-height:0;background:#fff;border:1px solid var(--line);border-radius:14px;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 8px 24px rgba(84,42,55,.04)}
      .xhs-empty{flex:1;display:grid;place-items:center;padding:26px;text-align:center}
      .xhs-empty .ico{font-size:32px}
      .xhs-empty h3{margin:9px 0 5px;font-size:15.5px}
      .xhs-empty p{margin:0;color:var(--muted);font-size:12.5px;line-height:1.7}
      .xhs-steps{display:flex;gap:7px;margin-top:14px;flex-wrap:wrap;justify-content:center}
      .xhs-steps span{font-size:11.5px;color:var(--muted);background:#faf5f6;border:1px solid #f1e4e8;border-radius:99px;padding:4px 9px}
      .xhs-recent{margin-top:16px;text-align:left;max-width:520px;width:100%}
      .xhs-recent h4{margin:0 0 7px;font-size:11.5px;color:var(--muted);font-weight:600}
      .xhs-recent .row{display:flex;align-items:center;gap:8px;padding:7px 9px;border:1px solid var(--line);border-radius:8px;margin-bottom:5px;font-size:11.5px;cursor:pointer;background:#fff}
      .xhs-recent .row:hover{border-color:#e6c6d0;background:#fffafb}
      .xhs-recent .row .t{flex:1;color:var(--muted)}
      .xhs-toolbar{flex:none;display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:9px 11px;border-bottom:1px solid var(--line)}
      .xhs-toolbar strong{font-size:12.5px}
      .xhs-toolbar .meta{font-size:11.5px;color:var(--muted)}
      .xhs-toolbar .spacer{flex:1}
      .xhs-topics{flex:1;min-height:0;overflow:auto;padding:10px;display:flex;flex-direction:column;gap:7px}
      .xhs-topic{display:flex;gap:9px;border:1px solid var(--line);border-radius:10px;padding:9px 10px;background:#fff;transition:.15s;min-width:0}
      .xhs-topic.on{border-color:#f0bcc9;background:#fffafb;box-shadow:0 0 0 2px rgba(255,46,85,.05)}
      .xhs-topic .pick{flex:none;padding-top:2px}
      .xhs-topic input[type=checkbox]{width:15px;height:15px;accent-color:var(--rose);cursor:pointer}
      .xhs-topic .main{flex:1;min-width:0;display:flex;flex-direction:column;gap:4px}
      .xhs-topic .title{border:0;background:transparent;padding:0;font-size:13px;font-weight:650;color:var(--ink);width:100%}
      .xhs-topic .title:focus{outline:none;background:#fff;box-shadow:0 0 0 2px rgba(255,46,85,.12);border-radius:4px;padding:2px 4px;margin:-2px -4px}
      .xhs-topic .angle{border:0;background:transparent;padding:0;font-size:11.5px;color:var(--muted);width:100%}
      .xhs-topic .angle:focus{outline:none;background:#fff;box-shadow:0 0 0 2px rgba(255,46,85,.12);border-radius:4px;padding:2px 4px;margin:-2px -4px}
      .xhs-topic .facts{font-size:11px;color:#8a7b83;line-height:1.55;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
      .xhs-topic .src{flex:none;align-self:flex-start;font-size:10px;color:var(--muted);background:#faf5f6;border:1px solid #f1e4e8;border-radius:99px;padding:2px 7px;max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      .xhs-prog{padding:14px;display:flex;flex-direction:column;gap:9px;min-height:0;flex:1}
      .xhs-prog .top{display:flex;align-items:baseline;justify-content:space-between;gap:10px}
      .xhs-prog .stage{font-size:13.5px;font-weight:650}
      .xhs-prog .pct{font-size:11.5px;color:var(--muted);font-variant-numeric:tabular-nums}
      .xhs-bar-track{height:6px;border-radius:99px;background:#f5ecef;overflow:hidden}
      .xhs-bar-fill{height:100%;background:linear-gradient(90deg,#ff6b8a,#ff2e55);border-radius:99px;transition:width .35s ease}
      .xhs-log{flex:1;min-height:110px;margin:0;padding:9px 11px;border-radius:9px;background:#1c1719;color:#e9dfe3;
        font:11px/1.62 ui-monospace,SFMono-Regular,Menlo,monospace;overflow:auto;white-space:pre-wrap;word-break:break-word}
      .xhs-log .ln{display:block}
      .xhs-summary{flex:none;display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:9px 11px;border-bottom:1px solid var(--line)}
      .xhs-summary strong{font-size:12.5px}
      .xhs-summary .meta{font-size:11.5px;color:var(--muted)}
      .xhs-summary .spacer{flex:1}
      .xhs-grid{flex:1;min-height:0;overflow:auto;padding:11px;display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(184px,1fr));align-content:start}
      .xhs-note{position:relative;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:#fff;cursor:pointer;transition:.16s;min-width:0;text-align:left;padding:0;font:inherit}
      .xhs-note:hover{transform:translateY(-2px);box-shadow:0 10px 22px rgba(90,40,55,.12);border-color:#efc9d3}
      .xhs-note .thumb{aspect-ratio:3/4;background:#f7f1f2;display:block;width:100%;object-fit:cover;object-position:top}
      .xhs-note .cap{padding:8px 9px 9px;display:block}
      .xhs-note .tt{font-size:12px;line-height:1.45;font-weight:600;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
      .xhs-note .tg{margin-top:4px;font-size:10.5px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:block}
      .xhs-note .badge{position:absolute;top:7px;left:7px;background:rgba(20,14,17,.62);color:#fff;font-size:10px;padding:2px 6px;border-radius:99px;backdrop-filter:blur(4px)}
      .xhs-modal{position:fixed;inset:0;z-index:50;background:rgba(28,20,24,.55);backdrop-filter:blur(6px);display:grid;place-items:center;padding:22px}
      .xhs-modal-body{width:min(1080px,100%);height:min(760px,100%);background:#fff;border-radius:16px;display:grid;grid-template-columns:minmax(0,1fr) 340px;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.35)}
      .xhs-stage{position:relative;background:#141013;display:flex;align-items:center;justify-content:center;min-width:0;min-height:0}
      .xhs-stage img{max-width:100%;max-height:100%;object-fit:contain;display:block}
      .xhs-nav{position:absolute;top:50%;transform:translateY(-50%);width:34px;height:34px;border-radius:50%;border:0;background:rgba(255,255,255,.9);color:#221a1e;font-size:17px;cursor:pointer;display:grid;place-items:center}
      .xhs-nav:disabled{opacity:.25;cursor:default}
      .xhs-nav.prev{left:10px}.xhs-nav.next{right:10px}
      .xhs-thumbs{position:absolute;bottom:8px;left:0;right:0;display:flex;justify-content:center;gap:5px;padding:0 8px;overflow:auto}
      .xhs-thumbs button{width:32px;height:43px;border-radius:4px;border:2px solid transparent;padding:0;overflow:hidden;background:#000;cursor:pointer;flex:none}
      .xhs-thumbs button.on{border-color:var(--rose)}
      .xhs-thumbs img{width:100%;height:100%;object-fit:cover;display:block;opacity:.7}
      .xhs-thumbs button.on img{opacity:1}
      .xhs-side-panel{display:flex;flex-direction:column;min-height:0;border-left:1px solid var(--line)}
      .xhs-side-panel .head{padding:12px 13px 9px;border-bottom:1px solid var(--line)}
      .xhs-side-panel .head h3{margin:0 0 5px;font-size:14px;line-height:1.45}
      .xhs-side-panel .tags{font-size:11px;color:#c8193b;line-height:1.6;overflow-wrap:anywhere}
      .xhs-side-panel .cap{flex:1;min-height:0;overflow:auto;padding:10px 13px;font-size:12px;line-height:1.75;white-space:pre-wrap;overflow-wrap:anywhere;color:#3a2f34}
      .xhs-side-panel .foot{padding:9px 13px;border-top:1px solid var(--line);display:flex;gap:7px;flex-wrap:wrap}
      .xhs-banner{margin:0 11px;padding:8px 11px;border-radius:9px;font-size:12px;line-height:1.55;display:flex;align-items:center;gap:9px;flex-wrap:wrap}
      .xhs-banner.warn{background:#fff8ec;border:1px solid #f3e1c2;color:#8a5d0a}
      .xhs-banner.err{background:#fff0f2;border:1px solid #f5cdd6;color:#ac1733}
      .xhs-banner .spacer{flex:1}
      .xhs-toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:#2a2126;color:#fff;font-size:12px;
        padding:8px 15px;border-radius:99px;box-shadow:0 10px 30px rgba(0,0,0,.24);z-index:60}
      .xhs-root.chat .xhs-body{padding-right:441px}
      .xhs-chat{position:absolute;top:0;right:0;bottom:0;width:min(430px,94%);background:#fff;border-left:1px solid var(--line);
        display:flex;flex-direction:column;z-index:30;box-shadow:-18px 0 48px rgba(40,20,28,.18)}
      .xhs-chat-head{flex:none;display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid var(--line)}
      .xhs-chat-head strong{font-size:12.5px}
      .xhs-chat-head .spacer{flex:1}
      .xhs-chat-body{flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden}
      .xhs-chat-empty{margin:auto;max-width:240px;text-align:center;color:var(--muted);font-size:12px;line-height:1.7;padding:18px}
      .xhs-chat-empty strong{display:block;color:var(--ink);font-size:13px;margin-bottom:6px}
      .xhs-drawer{position:fixed;inset:0;z-index:55;background:rgba(28,20,24,.45);backdrop-filter:blur(4px);display:flex;justify-content:flex-end}
      .xhs-drawer-body{width:min(560px,100%);height:100%;background:#fff;display:flex;flex-direction:column;box-shadow:-20px 0 60px rgba(0,0,0,.25)}
      .xhs-drawer-head{flex:none;padding:13px 15px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:10px}
      .xhs-drawer-head h2{margin:0;font-size:14.5px}
      .xhs-drawer-head .spacer{flex:1}
      .xhs-drawer-body .scroll{flex:1;min-height:0;overflow:auto;padding:12px 15px 20px}
      .xhs-tpl{border:1px solid var(--line);border-radius:10px;padding:10px;margin-bottom:9px}
      .xhs-tpl .row{display:flex;align-items:baseline;gap:7px}
      .xhs-tpl .row strong{font-size:13px}
      .xhs-tpl .badge{font-size:10px;color:#c8193b;background:var(--rose-soft);border-radius:99px;padding:1px 6px}
      .xhs-tpl p{margin:4px 0 0;font-size:11.5px;color:var(--muted);line-height:1.55}
      .xhs-tpl .acts{margin-top:7px;display:flex;gap:6px}
      .xhs-divider{margin:16px 0 10px;padding-top:14px;border-top:1px solid var(--line);font-size:12px;font-weight:650}
      .xhs-layouts{display:grid;grid-template-columns:1fr 1fr;gap:8px}
      .xhs-layouts div{border:1px solid var(--line);border-radius:9px;padding:8px 9px;font-size:11.5px;color:var(--muted)}
      .xhs-layouts b{display:block;font-size:12px;color:var(--ink);margin-bottom:2px}
      .xhs-modes{display:flex;gap:4px;border:1px solid var(--line);border-radius:13px;background:#f5edef;padding:4px}
      .xhs-modes button{flex:1;border:0;background:transparent;border-radius:9px;padding:7px 4px;font:inherit;font-size:12px;
        color:var(--muted);cursor:pointer;transition:.16s}
      .xhs-modes button:hover{color:var(--ink)}
      .xhs-modes button.on{background:#fff;color:var(--ink);font-weight:600;box-shadow:0 2px 7px rgba(84,42,55,.10)}
      .xhs-plans{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;padding:12px;overflow:auto;align-content:start}
      .xhs-plan{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:13px;display:flex;flex-direction:column;gap:8px;cursor:pointer}
      .xhs-plan:hover{border-color:#e7bcc6}
      .xhs-plan.on{border-color:var(--rose);box-shadow:0 12px 26px -20px rgba(255,46,85,.65)}
      .xhs-plan .head{display:flex;align-items:center;gap:7px;font-size:11px;color:var(--muted)}
      .xhs-plan .head b{font-size:12px;color:var(--ink)}
      .xhs-plan .badge{background:var(--rose);color:#fff;border-radius:5px;padding:2px 6px;font-size:10.5px}
      .xhs-plan h4{margin:0;font-size:15px;line-height:1.35}
      .xhs-plan .aud{font-size:11.5px;color:var(--muted)}
      .xhs-plan .cats{display:flex;flex-wrap:wrap;gap:4px}
      .xhs-plan .cats span{font-size:10.5px;background:#f6f1f3;border-radius:999px;padding:2px 7px;color:#5c4b52}
      .xhs-plan .prev{display:flex;gap:6px;flex-wrap:wrap;font-size:10.5px;color:#9a8a90}
      .xhs-pack-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
      .xhs-pack-item{display:flex;flex-direction:column;gap:6px}
      .xhs-pack-item button{border:0;padding:0;background:transparent;cursor:zoom-in;border-radius:10px;overflow:hidden;box-shadow:0 8px 18px -14px rgba(60,20,30,.45)}
      .xhs-pack-item img{width:100%;display:block;aspect-ratio:3/4;object-fit:cover}
      .xhs-pack-item .lbl{font-size:11px;color:var(--muted);text-align:center}
      .xhs-batch-grid{flex:1;min-height:0;overflow:auto;padding:12px;display:grid;
        grid-template-columns:repeat(auto-fill,minmax(186px,1fr));gap:12px;align-content:start}
      .xhs-batch-card{background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden;
        display:flex;flex-direction:column;min-width:0}
      .xhs-batch-card .cover{padding:0;border:0;background:#f6f1f2;cursor:pointer;display:block;line-height:0}
      .xhs-batch-card .cover img{width:100%;aspect-ratio:3/4;object-fit:cover;object-position:top;display:block}
      .xhs-batch-card h5{margin:9px 10px 3px;font-size:12.5px;line-height:1.45;color:var(--ink);
        overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
      .xhs-batch-card p{margin:0 10px;font-size:11px;color:var(--muted)}
      .xhs-batch-card footer{display:flex;justify-content:space-between;gap:6px;padding:9px 10px 11px;font-size:10.5px;color:var(--muted)}
      .xhs-pack-body{flex:1;min-height:0;display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:12px;padding:12px;overflow:hidden}
      .xhs-pack-imgs{min-height:0;overflow:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));
        align-content:start;gap:10px;padding-right:2px}
      .xhs-pack-doc{min-height:0;overflow:auto;background:#fbf7f8;border:1px solid var(--line);border-radius:12px;padding:12px 13px}
      .xhs-pack-doc h4{margin:0 0 8px;font-size:12px;color:var(--ink);display:flex;align-items:center;gap:8px}
      .xhs-pack-doc h4 span{margin-left:auto;font-size:10.5px;color:var(--muted);font-weight:400}
      .xhs-pack-doc pre{margin:0;white-space:pre-wrap;word-break:break-word;font:inherit;font-size:12.5px;line-height:1.85;color:#3a2e33}
      .xhs-caption{margin-top:12px;background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 14px;
        font-size:12px;line-height:1.75;white-space:pre-wrap;max-height:210px;overflow:auto;color:#3a2e33}
      @container (max-width:1100px){
        .xhs-pack-body{grid-template-columns:1fr;overflow:auto}
        .xhs-pack-imgs{overflow:visible}
        .xhs-pack-doc{overflow:visible}
      }
      @container (max-width:1000px){
        .xhs-root.chat .xhs-body{padding-right:9px}
        .xhs-chat{width:min(400px,96%)}
      }
      @container (max-width:900px){
        .xhs-body{display:flex;flex-direction:column;overflow:auto;padding:9px;gap:9px}
        .xhs-side{overflow:visible;flex:none;padding-right:0;display:grid;
          grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;align-content:start}
        .xhs-side > .xhs-modes{grid-column:1/-1}
        .xhs-side > .xhs-card:first-of-type{grid-column:1/-1}
        .xhs-side > .xhs-card:last-child{grid-column:1/-1}
        .xhs-side > .xhs-card{padding:10px 11px;border-radius:13px}
        .xhs-side > .xhs-card p{display:none}
        .xhs-side > .xhs-card h2{margin-bottom:6px;font-size:12.5px}
        .xhs-side > .xhs-card .xhs-field{margin-bottom:6px}
        .xhs-main{flex:none;min-height:520px;overflow:visible}
        .xhs-panel{min-height:480px}
        .xhs-grid{grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px;overflow:visible}
        .xhs-plans{grid-template-columns:repeat(2,minmax(0,1fr));padding:10px;overflow:visible}
        .xhs-batch-grid{grid-template-columns:repeat(auto-fill,minmax(150px,1fr));padding:10px}
        .xhs-modal-body{grid-template-columns:minmax(0,1fr);grid-template-rows:minmax(0,1fr) 44%}
        .xhs-side-panel{border-left:0;border-top:1px solid var(--line)}
      }
      @container (max-width:560px){
        .xhs-side{grid-template-columns:1fr}
        .xhs-plans{grid-template-columns:1fr}
        .xhs-brand p{display:none}
        .xhs-bar{padding:9px 11px}
        .xhs-modal{padding:0}
        .xhs-modal-body{height:100%;border-radius:0}
        .xhs-row{grid-template-columns:1fr}
      }
    `

    const DEFAULT_SETTINGS = {
      count: 6, topic: '', audience: '25-35 岁女性',
      writing: 'listicle', cover: 'poster', card: 'index', palette: 'warm',
      cards: 4, signature: '', noFix: false,
    }

    async function readEntry(entry, output) {
      if (!entry) return
      if (entry.isFile) {
        const file = await new Promise((resolve, reject) => entry.file(resolve, reject)).catch(() => null)
        if (file) output.push(file)
        return
      }
      if (entry.isDirectory) {
        const reader = entry.createReader()
        while (true) {
          const batch = await new Promise((resolve, reject) => reader.readEntries(resolve, reject)).catch(() => [])
          if (!batch || !batch.length) break
          for (const child of batch) await readEntry(child, output)
        }
      }
    }

    async function collectDrop(dataTransfer) {
      const items = Array.from((dataTransfer && dataTransfer.items) || [])
      const entries = items.map((item) => (item.webkitGetAsEntry ? item.webkitGetAsEntry() : null)).filter(Boolean)
      if (!entries.length) return Array.from((dataTransfer && dataTransfer.files) || [])
      const output = []
      for (const entry of entries) await readEntry(entry, output)
      return output
    }

    function readSettings() {
      try {
        const raw = JSON.parse(localStorage.getItem(SETTINGS_KEY) || 'null')
        return raw && typeof raw === 'object' ? { ...DEFAULT_SETTINGS, ...raw } : { ...DEFAULT_SETTINGS }
      } catch {
        return { ...DEFAULT_SETTINGS }
      }
    }

    function injectStyles() {
      if (document.querySelector('style[data-xhs-batch]')) return
      const node = document.createElement('style')
      node.dataset.xhsBatch = 'true'
      node.textContent = styles
      document.head.appendChild(node)
    }

    const formatSize = (bytes) => {
      if (!bytes) return '0 B'
      if (bytes < 1024) return `${bytes} B`
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
      return `${(bytes / 1024 / 1024).toFixed(1)} MB`
    }

    const extOf = (name) => (/\.([a-z0-9]+)$/i.exec(name || '') || [null, 'FILE'])[1].toUpperCase()

    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

    async function api(path, options = {}) {
      const response = await fetch(`${API}/${path}`, {
        cache: 'no-store',
        ...options,
        headers: { 'content-type': 'application/json', ...(options.headers || {}) },
      })
      let data = {}
      try {
        data = await response.json()
      } catch {
        throw new Error(`服务无响应（HTTP ${response.status}）`)
      }
      if (!response.ok || data.ok === false) throw new Error(data.error || `请求失败（HTTP ${response.status}）`)
      return data
    }

    // ------------------------------------------------------------ 子组件

    function Progress({ job, onCancel }) {
      const logRef = React.useRef(null)
      React.useEffect(() => {
        if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
      }, [job.lines.length])
      return h('div', { className: 'xhs-panel' },
        h('div', { className: 'xhs-prog' },
          h('div', { className: 'top' },
            h('div', { className: 'stage' }, job.stage || '处理中…'),
            h('div', { className: 'pct' }, `${job.progress || 0}%`)),
          h('div', { className: 'xhs-bar-track' }, h('div', { className: 'xhs-bar-fill', style: { width: `${job.progress || 3}%` } })),
          h('pre', { className: 'xhs-log', ref: logRef },
            (job.lines || []).map((line, index) => h('span', { className: 'ln', key: index }, line))),
          h('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 } },
            h('span', { style: { fontSize: 11, color: 'var(--muted)' } }, `已用时 ${job.elapsed || 0}s`),
            h('button', { className: 'xhs-btn danger', onClick: onCancel }, '取消任务'))))
    }

    function Preview({ result, index, imageIndex, onIndex, onClose, onToast }) {
      const note = result.notes[index]
      const total = note.images.length
      React.useEffect(() => {
        const handler = (event) => {
          if (event.key === 'Escape') onClose()
          if (event.key === 'ArrowRight') onIndex(index, Math.min(total - 1, imageIndex + 1))
          if (event.key === 'ArrowLeft') onIndex(index, Math.max(0, imageIndex - 1))
        }
        window.addEventListener('keydown', handler)
        return () => window.removeEventListener('keydown', handler)
      }, [index, imageIndex, total])
      return h('div', { className: 'xhs-modal', onClick: onClose },
        h('div', { className: 'xhs-modal-body', onClick: (event) => event.stopPropagation() },
          h('div', { className: 'xhs-stage' },
            h('img', { src: note.images[imageIndex]?.url, alt: note.title }),
            h('button', { className: 'xhs-nav prev', disabled: imageIndex === 0, onClick: () => onIndex(index, imageIndex - 1) }, '‹'),
            h('button', { className: 'xhs-nav next', disabled: imageIndex >= total - 1, onClick: () => onIndex(index, imageIndex + 1) }, '›'),
            total > 1 && h('div', { className: 'xhs-thumbs' },
              note.images.map((image, i) => h('button', {
                key: image.name, className: i === imageIndex ? 'on' : '', onClick: () => onIndex(index, i),
              }, h('img', { src: image.url, alt: '' }))))),
          h('aside', { className: 'xhs-side-panel' },
            h('div', { className: 'head' },
              h('h3', null, note.title),
              h('div', { className: 'tags' }, (note.caption.split('\n').pop() || '').slice(0, 120))),
            h('div', { className: 'cap' }, note.caption),
            h('div', { className: 'foot' },
              h('button', {
                className: 'xhs-btn primary',
                onClick: async () => {
                  try {
                    await navigator.clipboard.writeText(note.caption)
                    onToast('文案已复制')
                  } catch {
                    onToast('复制失败，请手动选择文本')
                  }
                },
              }, '复制文案'),
              h('a', { className: 'xhs-btn', href: note.images[imageIndex]?.url, target: '_blank', rel: 'noreferrer' }, '查看原图'),
              h('button', { className: 'xhs-btn ghost', onClick: onClose }, '关闭')))))
    }

    function NoteCard({ note, onOpen }) {
      const tags = (note.caption.split('\n').pop() || '').trim()
      return h('button', { className: 'xhs-note', onClick: onOpen, title: note.title },
        h('span', { className: 'badge' }, `${note.images.length} 张`),
        h('img', { className: 'thumb', src: note.images[0]?.url, alt: note.title, loading: 'lazy' }),
        h('span', { className: 'cap' },
          h('span', { className: 'tt' }, note.title),
          h('span', { className: 'tg' }, tags || '—')))
    }

    function TemplateDrawer({ catalog, onClose, onSave, onDelete, notify }) {
      const writing = Object.values(catalog?.writing || {})
      const covers = catalog?.covers || {}
      const cards = catalog?.cards || {}
      const empty = {
        id: '', name: '', desc: '', tone: '', title_rule: '', hook: '', cta: '',
        emoji: '每节最多 1 个', extra: '', sections: '3,5', lines: '2,4', tags: '6,8', line_max: 22, heading_max: 12,
      }
      const [form, setForm] = React.useState(null)
      const [saving, setSaving] = React.useState(false)
      const [error, setError] = React.useState('')

      const startNew = () => setForm({ ...empty })
      const startEdit = (template) => setForm({
        ...empty, ...template,
        sections: (template.sections || [3, 5]).join(','),
        lines: (template.lines || [2, 4]).join(','),
        tags: (template.tags || [6, 8]).join(','),
        id: template.builtin ? '' : template.id,
      })

      const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))

      async function save() {
        setError('')
        const parsePair = (text, fallback) => {
          const parts = String(text || '').split(/[,，\s]+/).map(Number).filter(Number.isFinite)
          return parts.length === 2 ? parts : fallback
        }
        const payload = {
          id: form.id, name: form.name || form.id, desc: form.desc, tone: form.tone,
          title_rule: form.title_rule, hook: form.hook, cta: form.cta, emoji: form.emoji,
          extra: form.extra, sections: parsePair(form.sections, [3, 5]), lines: parsePair(form.lines, [2, 4]),
          tags: parsePair(form.tags, [6, 8]), line_max: Number(form.line_max) || 22, heading_max: Number(form.heading_max) || 12,
        }
        if (!payload.id || !payload.name) {
          setError('请填写模板 id（英文）和名称')
          return
        }
        setSaving(true)
        try {
          await onSave(payload)
          notify('模板已保存')
          setForm(null)
        } catch (reason) {
          setError(reason.message || '保存失败')
        } finally {
          setSaving(false)
        }
      }

      return h('div', { className: 'xhs-drawer', onClick: onClose },
        h('div', { className: 'xhs-drawer-body', onClick: (event) => event.stopPropagation() },
          h('div', { className: 'xhs-drawer-head' },
            h('h2', null, '模板 / 技能'),
            h('span', { className: 'spacer' }),
            h('button', { className: 'xhs-btn primary', onClick: startNew }, '新建模板'),
            h('button', { className: 'xhs-btn ghost', onClick: onClose }, '关闭')),
          h('div', { className: 'scroll' },
            error && h('div', { className: 'xhs-banner err', style: { margin: '0 0 10px' } }, error),
            form && h('div', { className: 'xhs-card', style: { marginBottom: 12 } },
              h('h2', null, form.name ? `编辑：${form.name}` : '新建写作模板'),
              h('div', { className: 'xhs-row' },
                h('label', { className: 'xhs-field' },
                  h('span', { className: 'xhs-label' }, '模板 id', h('span', { className: 'xhs-hint' }, '英文，唯一')),
                  h('input', { value: form.id, disabled: Boolean(form.builtin), placeholder: 'my-style', onChange: (event) => update('id', event.target.value) })),
                h('label', { className: 'xhs-field' },
                  h('span', { className: 'xhs-label' }, '显示名称'),
                  h('input', { value: form.name, placeholder: '我的爆款结构', onChange: (event) => update('name', event.target.value) }))),
              h('label', { className: 'xhs-field' },
                h('span', { className: 'xhs-label' }, '一句话说明'),
                h('input', { value: form.desc, onChange: (event) => update('desc', event.target.value) })),
              h('div', { className: 'xhs-row' },
                h('label', { className: 'xhs-field' },
                  h('span', { className: 'xhs-label' }, '节数范围'),
                  h('input', { value: form.sections, placeholder: '3,5', onChange: (event) => update('sections', event.target.value) })),
                h('label', { className: 'xhs-field' },
                  h('span', { className: 'xhs-label' }, '每节行数'),
                  h('input', { value: form.lines, placeholder: '2,4', onChange: (event) => update('lines', event.target.value) }))),
              h('div', { className: 'xhs-row' },
                h('label', { className: 'xhs-field' },
                  h('span', { className: 'xhs-label' }, '标签数量'),
                  h('input', { value: form.tags, placeholder: '6,8', onChange: (event) => update('tags', event.target.value) })),
                h('label', { className: 'xhs-field' },
                  h('span', { className: 'xhs-label' }, '每行字数上限'),
                  h('input', { type: 'number', value: form.line_max, onChange: (event) => update('line_max', event.target.value) }))),
              h('label', { className: 'xhs-field' },
                h('span', { className: 'xhs-label' }, '语气'),
                h('input', { value: form.tone, placeholder: '条理清晰、具体、有数字', onChange: (event) => update('tone', event.target.value) })),
              h('label', { className: 'xhs-field' },
                h('span', { className: 'xhs-label' }, '标题规则'),
                h('input', { value: form.title_rule, onChange: (event) => update('title_rule', event.target.value) })),
              h('label', { className: 'xhs-field' },
                h('span', { className: 'xhs-label' }, '开头钩子'),
                h('input', { value: form.hook, onChange: (event) => update('hook', event.target.value) })),
              h('label', { className: 'xhs-field' },
                h('span', { className: 'xhs-label' }, '结尾引导'),
                h('input', { value: form.cta, onChange: (event) => update('cta', event.target.value) })),
              h('label', { className: 'xhs-field' },
                h('span', { className: 'xhs-label' }, '补充要求 ', h('span', { className: 'xhs-hint' }, '可直接粘贴你的写作 skill / 规则')),
                h('textarea', { value: form.extra, rows: 4, onChange: (event) => update('extra', event.target.value) })),
              h('div', { style: { display: 'flex', gap: 8, justifyContent: 'flex-end' } },
                h('button', { className: 'xhs-btn ghost', onClick: () => setForm(null) }, '取消'),
                h('button', { className: 'xhs-btn primary', disabled: saving, onClick: save }, saving ? '保存中…' : '保存模板'))),
            h('div', { className: 'xhs-divider', style: { marginTop: form ? 16 : 0 } }, `写作模板（${writing.length}）`),
            writing.map((template) => h('div', { className: 'xhs-tpl', key: template.id },
              h('div', { className: 'row' },
                h('strong', null, template.name),
                template.builtin && h('span', { className: 'badge' }, '内置'),
                h('span', { style: { marginLeft: 'auto', fontSize: 10.5, color: 'var(--muted)' } }, `${template.sections[0]}-${template.sections[1]} 节 · 每行≤${template.line_max}字`)),
              h('p', null, template.desc || '—'),
              h('div', { className: 'acts' },
                h('button', { className: 'xhs-btn', onClick: () => startEdit(template) }, template.builtin ? '另存为新模板' : '编辑'),
                !template.builtin && h('button', {
                  className: 'xhs-btn danger',
                  onClick: () => onDelete(template.id),
                }, '删除')))),
            h('div', { className: 'xhs-divider' }, '版式模板（固定版式，不抽卡）'),
            h('div', { className: 'xhs-layouts' },
              Object.entries(covers).map(([id, label]) => h('div', { key: id }, h('b', null, `封面 · ${label}`), '文字自动排版，尺寸固定 1080×1440')),
              Object.entries(cards).map(([id, label]) => h('div', { key: id }, h('b', null, `内页 · ${label}`), '要点自动适配字号'))))))
    }

    // ------------------------------------------------------------ 主面板

    function Panel({ service, conversation }) {
      injectStyles()
      const [env, setEnv] = React.useState({ ready: null, runs: [], catalog: { writing: {}, covers: {}, cards: {} } })
      const [offline, setOffline] = React.useState('')
      const [files, setFiles] = React.useState([])
      const [uploading, setUploading] = React.useState(0)
      const [cfg, setCfg] = React.useState(readSettings)
      const [analysis, setAnalysis] = React.useState(null)
      const [job, setJob] = React.useState(null)
      const [result, setResult] = React.useState(null)
      const [error, setError] = React.useState('')
      const [toast, setToast] = React.useState('')
      const [dragOver, setDragOver] = React.useState(false)
      const [preview, setPreview] = React.useState(null)
      const [drawer, setDrawer] = React.useState(false)
      const [chatOpen, setChatOpen] = React.useState(false)
      const [chatBusy, setChatBusy] = React.useState(false)
      const [mode, setMode] = React.useState('pack')
      const [pack, setPack] = React.useState(null)
      const [packIndex, setPackIndex] = React.useState(0)
      const [packResult, setPackResult] = React.useState(null)
      const [batch, setBatch] = React.useState(null)
      const [batchCount, setBatchCount] = React.useState(12)
      const [planCount, setPlanCount] = React.useState(3)
      const [batchPreview, setBatchPreview] = React.useState(null)
      const [historyOpen, setHistoryOpen] = React.useState(false)
      const [hasSession, setHasSession] = React.useState(false)
      const alive = React.useRef(true)
      const inputRef = React.useRef(null)
      const folderRef = React.useRef(null)

      React.useEffect(() => () => { alive.current = false }, [])

      const notify = React.useCallback((message) => {
        setToast(message)
        window.setTimeout(() => setToast(''), 1800)
      }, [])

      const refreshEnv = React.useCallback(async () => {
        try {
          const data = await api('env')
          if (!alive.current) return
          setEnv(data)
          setOffline('')
        } catch (reason) {
          if (alive.current) setOffline(reason.message || '后端服务不可用')
        }
      }, [])

      React.useEffect(() => { refreshEnv() }, [refreshEnv])

      const detectSession = React.useCallback(() => {
        try {
          const current = service?.currentSession?.()
          if (!current) return false
          try {
            return Boolean(service?.ownsSession?.(current))
          } catch {
            // 宿主在非插件上下文里可能拒绝 ownsSession，按“有会话”处理即可
            return true
          }
        } catch {
          return false
        }
      }, [service])

      React.useEffect(() => {
        setHasSession(detectSession())
      }, [detectSession, chatOpen, conversation])

      // 这个工作台一旦有了会话（比如用户点了左侧「新会话」），直接展开对话
      const autoOpened = React.useRef(false)
      React.useEffect(() => {
        if (hasSession && !autoOpened.current) {
          autoOpened.current = true
          setChatOpen(true)
        }
        if (!hasSession) autoOpened.current = false
      }, [hasSession])

      async function startConversation() {
        if (detectSession()) return
        setChatBusy(true)
        try {
          const workspace = service?.defaultWorkspace?.()
          if (workspace && service?.newSession) await service.newSession(workspace.workspaceId)
          else if (service?.newWorkspaceSession) await service.newWorkspaceSession()
        } catch (reason) {
          setError(reason instanceof Error ? reason.message : '暂时无法打开对话，请稍后重试')
        } finally {
          setChatBusy(false)
        }
      }

      function toggleChat() {
        if (chatOpen) {
          setChatOpen(false)
          return
        }
        setChatOpen(true)
        if (!hasSession) startConversation()
      }
      React.useEffect(() => {
        try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(cfg)) } catch { /* ignore */ }
      }, [cfg])

      const waitJob = React.useCallback(async (jobId) => {
        while (alive.current) {
          const data = await api(`job?id=${encodeURIComponent(jobId)}`)
          if (!alive.current) return null
          setJob(data.job)
          if (data.job.status !== 'running') return data.job
          await sleep(800)
        }
        return null
      }, [])

      async function addFiles(list) {
        const picked = Array.from(list || []).slice(0, 300)
        if (!picked.length) return
        setError('')
        setUploading(picked.length)
        try {
          for (const file of picked) {
            if (!/\.(xlsx|xlsm|xls|csv|pdf|docx|doc|md|txt)$/i.test(file.name)) {
              setError(`不支持的格式：${file.name}`)
              setUploading((value) => Math.max(0, value - 1))
              continue
            }
            const response = await fetch(`${API}/upload?name=${encodeURIComponent(file.name)}`, { method: 'POST', body: file })
            const data = await response.json().catch(() => ({}))
            if (!response.ok || data.ok === false) throw new Error(data.error || `上传失败：${file.name}`)
            setFiles((prev) => (prev.some((item) => item.id === data.id) ? prev : [...prev, { id: data.id, name: data.name, size: data.size }]))
            setUploading((value) => Math.max(0, value - 1))
          }
        } catch (reason) {
          setError(reason.message || '上传失败')
        } finally {
          setUploading(0)
        }
      }

      const removeFile = (id) => setFiles((prev) => prev.filter((item) => item.id !== id))

      async function ensureReady() {
        let state = await api('env')
        setEnv(state)
        if (state.ready) return true
        const prep = await api('prepare', { method: 'POST' })
        const done = await waitJob(prep.jobId)
        if (!done) return false
        if (done.status !== 'done') throw new Error(done.error || '环境准备失败')
        state = await api('env')
        setEnv(state)
        if (!state.ready) throw new Error('环境仍未就绪，请检查日志')
        return true
      }

      async function analyze() {
        if (!files.length) {
          setError('先添加至少一份资料')
          return
        }
        setError('')
        setResult(null)
        setJob({ status: 'running', stage: '检查环境', progress: 0, lines: [] })
        try {
          await ensureReady()
          const started = await api('analyze', {
            method: 'POST',
            body: JSON.stringify({
              uploads: files.map((item) => item.id),
              config: { count: cfg.count, topic: cfg.topic, audience: cfg.audience },
            }),
          })
          const finished = await waitJob(started.jobId)
          if (!finished || finished.status === 'cancelled') return
          if (finished.status === 'failed') throw new Error(finished.error || '解析失败')
          const topics = (finished.result?.topics || []).map((topic, index) => ({
            ...topic, id: topic.id || `t${index}`, selected: true,
          }))
          if (!topics.length) throw new Error('没有提炼出选题')
          setAnalysis({ runId: finished.result.runId, topics })
          notify(`提炼出 ${topics.length} 个选题，勾选后生成`)
        } catch (reason) {
          setError(reason.message || '解析失败')
        } finally {
          if (alive.current) setJob(null)
        }
      }

      async function generate() {
        const picked = (analysis?.topics || []).filter((topic) => topic.selected)
        if (!picked.length) {
          setError('先勾选至少一个选题')
          return
        }
        setError('')
        setResult(null)
        setJob({ status: 'running', stage: '准备生成', progress: 0, lines: [] })
        try {
          const started = await api('generate', {
            method: 'POST',
            body: JSON.stringify({
              runId: analysis.runId,
              topics: picked.map((topic) => ({
                id: topic.id, title: topic.title, angle: topic.angle,
                audience: topic.audience, key_facts: topic.key_facts, source: topic.source,
              })),
              config: {
                count: picked.length, writing: cfg.writing, cover: cfg.cover, card: cfg.card,
                palette: cfg.palette, cards: cfg.cards, signature: cfg.signature, noFix: cfg.noFix,
              },
            }),
          })
          const finished = await waitJob(started.jobId)
          if (!finished || finished.status === 'cancelled') {
            notify('任务已取消')
            return
          }
          if (finished.status === 'failed') throw new Error(finished.error || '生成失败')
          if (finished.result?.notes?.length) {
            setResult(finished.result)
            notify(`生成完成：${finished.result.notes.length} 篇`)
            refreshEnv()
          } else {
            throw new Error('没有生成任何笔记，请查看日志')
          }
        } catch (reason) {
          setError(reason.message || '生成失败')
        } finally {
          if (alive.current) setJob(null)
        }
      }


      async function analyzePack() {
        if (!files.length) {
          setError('先添加至少一份资料')
          return
        }
        setError('')
        setPack(null)
        setPackResult(null)
        setBatch(null)
        setJob({ status: 'running', stage: '检查环境', progress: 0, lines: [] })
        try {
          await ensureReady()
          const started = await api('pack/analyze', {
            method: 'POST',
            body: JSON.stringify({ uploads: files.map((item) => item.id), count: planCount }),
          })
          const finished = await waitJob(started.jobId)
          if (!finished || finished.status === 'cancelled') return
          if (finished.status === 'failed') throw new Error(finished.error || '生成方案失败')
          if (!finished.result?.plans?.length) throw new Error('没有生成可用方案')
          setPack({ runId: finished.result.runId, plans: finished.result.plans, files: finished.result.files || [] })
          setPackIndex(0)
          notify(`生成了 ${finished.result.plans.length} 套方案，选一套出图`)
        } catch (reason) {
          setError(reason.message || '生成方案失败')
        } finally {
          if (alive.current) setJob(null)
        }
      }

      async function generatePack(index = packIndex) {
        const plan = pack?.plans?.[index]
        if (!plan) {
          setError('先生成方案')
          return
        }
        setPackIndex(index)
        setError('')
        setPackResult(null)
        setJob({ status: 'running', stage: '按方案出图', progress: 0, lines: [] })
        try {
          const started = await api('pack/generate', {
            method: 'POST',
            body: JSON.stringify({ runId: pack.runId, plan }),
          })
          const finished = await waitJob(started.jobId)
          if (!finished || finished.status === 'cancelled') {
            notify('任务已取消')
            return
          }
          if (finished.status === 'failed') throw new Error(finished.error || '出图失败')
          if (!finished.result?.images?.length) throw new Error('没有生成图片')
          setPackResult(finished.result)
          notify('6 张图生成完成')
          refreshEnv()
        } catch (reason) {
          setError(reason.message || '出图失败')
        } finally {
          if (alive.current) setJob(null)
        }
      }

      async function runBatch() {
        const runId = pack?.runId || packResult?.runId || batch?.runId || ''
        if (!runId) {
          setError('先生成方案，再批量出图')
          return
        }
        setError('')
        setBatch(null)
        setBatchPreview(null)
        setJob({ status: 'running', stage: '编排方案中', progress: 0, lines: [] })
        try {
          const started = await api('pack/batch', {
            method: 'POST',
            body: JSON.stringify({ runId, count: batchCount }),
          })
          const finished = await waitJob(started.jobId)
          if (!finished || finished.status === 'cancelled') {
            notify('任务已取消')
            return
          }
          if (finished.status === 'failed') throw new Error(finished.error || '批量出图失败')
          if (!finished.result?.notes?.length) throw new Error('没有生成任何笔记')
          setBatch(finished.result)
          setPackResult(null)
          notify(`批量完成：${finished.result.notes.length} 条`)
          refreshEnv()
        } catch (reason) {
          setError(reason.message || '批量出图失败')
        } finally {
          if (alive.current) setJob(null)
        }
      }

      async function revealPack() {
        const runId = packResult?.runId || pack?.runId || ''
        try {
          await api(`reveal${runId ? `?runId=${encodeURIComponent(runId)}` : ''}`, { method: 'POST' })
        } catch (reason) {
          setError(reason.message || '无法打开文件夹')
        }
      }

      async function copyCaption(text) {
        try {
          await navigator.clipboard.writeText(text)
          notify('文案已复制')
        } catch {
          notify('复制失败，请手动选择文本')
        }
      }

      async function cancel() {
        if (!job?.id) return
        try { await api(`cancel?id=${encodeURIComponent(job.id)}`, { method: 'POST' }) } catch { /* ignore */ }
      }

      async function prepareEnv() {
        setError('')
        setJob({ status: 'running', stage: '准备运行环境', progress: 0, lines: [] })
        try {
          const prep = await api('prepare', { method: 'POST' })
          const done = await waitJob(prep.jobId)
          if (done?.status === 'done') {
            await refreshEnv()
            notify('环境已就绪')
          } else if (done) {
            throw new Error(done.error || '环境准备失败')
          }
        } catch (reason) {
          setError(reason.message || '环境准备失败')
        } finally {
          if (alive.current) setJob(null)
        }
      }

      async function openRun(runId) {
        setError('')
        try {
          const [resultData, topicsData] = await Promise.all([
            api(`result?runId=${encodeURIComponent(runId)}`),
            api(`topics?runId=${encodeURIComponent(runId)}`),
          ])
          if (resultData.result.notes.length) setResult(resultData.result)
          if (topicsData.topics.length) {
            setAnalysis({
              runId,
              topics: topicsData.topics.map((topic, index) => ({ ...topic, id: topic.id || `t${index}`, selected: false })),
            })
          }
        } catch (reason) {
          setError(reason.message || '读取历史记录失败')
        }
      }

      async function openHistory(run) {
        setError('')
        setHistoryOpen(false)
        try {
          const data = await api(`history/open?runId=${encodeURIComponent(run.runId)}`)
          if (data.kind === 'batch') {
            setMode('pack'); setPack(null); setPackResult(null); setBatch(data.result)
            return
          }
          if (data.kind === 'pack') {
            setMode('pack'); setBatch(null); setPackResult(data.result)
            return
          }
          setMode('notes')
          if (data.topics?.length) {
            setAnalysis({
              runId: run.runId,
              topics: data.topics.map((topic, index) => ({ ...topic, id: topic.id || `t${index}`, selected: false })),
            })
          }
          await openRun(run.runId)
        } catch (reason) {
          setError(reason?.message || '打开历史记录失败')
        }
      }

      async function reveal() {
        try {
          const runId = result?.runId || analysis?.runId || ''
          await api(`reveal${runId ? `?runId=${encodeURIComponent(runId)}` : ''}`, { method: 'POST' })
        } catch (reason) {
          setError(reason.message || '无法打开文件夹')
        }
      }

      const toggleTopic = (id) => setAnalysis((current) => ({
        ...current,
        topics: current.topics.map((topic) => (topic.id === id ? { ...topic, selected: !topic.selected } : topic)),
      }))

      const editTopic = (id, patch) => setAnalysis((current) => ({
        ...current,
        topics: current.topics.map((topic) => (topic.id === id ? { ...topic, ...patch } : topic)),
      }))

      const setAll = (selected) => setAnalysis((current) => ({
        ...current,
        topics: current.topics.map((topic) => ({ ...topic, selected })),
      }))

      async function saveTemplate(payload) {
        const data = await api('templates', { method: 'POST', body: JSON.stringify({ template: payload }) })
        setEnv((current) => ({ ...current, catalog: data.catalog }))
      }

      async function deleteTemplate(id) {
        const data = await api('templates/delete', { method: 'POST', body: JSON.stringify({ id }) })
        setEnv((current) => ({ ...current, catalog: data.catalog }))
        notify('模板已删除')
      }

      const running = Boolean(job)
      const selectedCount = (analysis?.topics || []).filter((topic) => topic.selected).length
      const writingTemplates = Object.values(env.catalog?.writing || {})

      const envChip = offline
        ? h('span', { className: 'xhs-chip warn' }, h('span', { className: 'dot' }), '服务未连接')
        : env.ready === true
          ? h('span', { className: 'xhs-chip ok' }, h('span', { className: 'dot' }), '环境就绪')
          : env.ready === false
            ? h('span', { className: 'xhs-chip warn' }, h('span', { className: 'dot' }), '需要准备环境')
            : h('span', { className: 'xhs-chip' }, h('span', { className: 'dot' }), '检查中…')

      const side = h('aside', { className: 'xhs-side' },
        h('div', { className: 'xhs-modes' },
          h('button', { className: mode === 'pack' ? 'on' : '', onClick: () => setMode('pack') }, '资料包'),
          h('button', { className: mode === 'notes' ? 'on' : '', onClick: () => setMode('notes') }, '知识笔记')),
        h('section', { className: 'xhs-card' },
          h('h2', null, h('span', { className: 'xhs-step' }, '1'), '导入资料', h('span', { className: 'state' }, `${files.length} 份`)),
          h('div', {
            className: `xhs-drop${dragOver ? ' over' : ''}`,
            onClick: () => inputRef.current?.click(),
            onDragOver: (event) => { event.preventDefault(); setDragOver(true) },
            onDragLeave: () => setDragOver(false),
            onDrop: async (event) => {
              event.preventDefault()
              setDragOver(false)
              const dropped = await collectDrop(event.dataTransfer)
              addFiles(dropped)
            },
          },
            h('strong', null, uploading ? `上传中…（剩 ${uploading}）` : '拖入文件夹 / 文件，或点击选择'),
            'Excel / PDF / Word / CSV，扫描件自动 OCR'),
          h('input', {
            ref: inputRef, type: 'file', multiple: true, hidden: true,
            accept: '.xlsx,.xlsm,.xls,.csv,.pdf,.docx,.doc,.md,.txt',
            onChange: (event) => { addFiles(event.target.files); event.target.value = '' },
          }),
          h('input', {
            ref: folderRef, type: 'file', multiple: true, hidden: true, webkitdirectory: '',
            onChange: (event) => { addFiles(event.target.files); event.target.value = '' },
          }),
          h('div', { style: { display: 'flex', gap: 6, marginTop: 7 } },
            h('button', { className: 'xhs-btn', style: { flex: 1, fontSize: 11 }, onClick: () => inputRef.current?.click() }, '选文件'),
            h('button', { className: 'xhs-btn', style: { flex: 1, fontSize: 11 }, onClick: () => folderRef.current?.click() }, '选文件夹'),
          files.length > 0 && h('button', {
            className: 'xhs-btn ghost', style: { flex: '0 0 auto', fontSize: 11, padding: '0 10px' },
            title: '移除全部已选资料', onClick: () => setFiles([]),
          }, '清空')),
          files.length > 0 && h('ul', { className: 'xhs-files' },
            files.map((file) => h('li', { className: 'xhs-file', key: file.id },
              h('span', { className: 'ext' }, extOf(file.name)),
              h('span', { className: 'nm', title: file.name }, file.name),
              h('span', { className: 'sz' }, formatSize(file.size)),
              h('button', { onClick: () => removeFile(file.id), 'aria-label': `移除 ${file.name}` }, '×')))),
          h('div', { style: { height: 9 } }),
          mode === 'notes' && h('label', { className: 'xhs-field' },
            h('span', { className: 'xhs-label' }, '内容方向 ', h('span', { className: 'xhs-hint' }, '可选')),
            h('input', { value: cfg.topic, maxLength: 60, placeholder: '如：小户型收纳 / 减脂餐', onChange: (event) => setCfg({ ...cfg, topic: event.target.value }) })),
          mode === 'notes' && h('label', { className: 'xhs-field' },
            h('span', { className: 'xhs-label' }, '选题数量'),
            h('select', { value: cfg.count, onChange: (event) => setCfg({ ...cfg, count: Number(event.target.value) }) },
              [4, 6, 8, 10, 12, 15].map((value) => h('option', { key: value, value }, `${value} 个选题`)))),
          mode === 'notes' && h('button', {
            className: 'xhs-btn primary', style: { width: '100%', padding: 9 },
            disabled: running || !files.length, onClick: analyze,
          },
            analysis ? '重新提炼选题' : '提炼选题')),
        mode === 'pack' && h(React.Fragment, null,
          h('section', { className: 'xhs-card' },
            h('h2', null, h('span', { className: 'xhs-step' }, '2'), '生成方案',
              h('span', { className: 'state' }, pack?.plans ? `${pack.plans.length} 套` : '待生成')),
            h('p', { style: { margin: 0, fontSize: 11.5, color: 'var(--muted)', lineHeight: 1.6 } },
              '模型读完资料给几套不同人群的方案，在右侧选一套。'),
            h('label', { className: 'xhs-field', style: { marginTop: 8 } },
              h('span', { className: 'xhs-label' }, '生成几套'),
              h('select', { value: planCount, onChange: (event) => setPlanCount(Number(event.target.value)) },
                [1, 2, 3, 4, 5, 6].map((value) => h('option', { key: value, value }, `${value} 套`)))),
            h('div', { style: { height: 8 } }),
            h('button', {
              className: 'xhs-btn primary', style: { width: '100%', padding: 9 },
              disabled: running || !files.length, onClick: analyzePack,
            }, pack?.plans ? '重新生成方案' : `生成 ${planCount} 套方案`)),
          h('section', { className: 'xhs-card' },
            h('h2', null, h('span', { className: 'xhs-step' }, '3'), '出图',
              h('span', { className: 'state' }, packResult ? '已完成' : pack?.plans ? `第 ${packIndex + 1} 套` : '待选')),
            h('p', { style: { margin: 0, fontSize: 11.5, color: 'var(--muted)', lineHeight: 1.6 } },
              packResult ? '已出 6 张图，可打包下载或换一套重出。' : '选中方案按固定版式渲染 6 张图 + 文案。'),
            h('div', { style: { height: 8 } }),
            h('button', {
              className: 'xhs-btn primary', style: { width: '100%', padding: 9 },
              disabled: running || !pack?.plans, onClick: () => generatePack(),
            }, packResult ? '重新出图' : '生成 6 张图')),
          h('section', { className: 'xhs-card' },
            h('h2', null, h('span', { className: 'xhs-step' }, '4'), '批量',
              h('span', { className: 'state' }, batch ? `${batch.count} 条` : '待生成')),
            h('p', { style: { margin: 0, fontSize: 11.5, color: 'var(--muted)', lineHeight: 1.6 } },
              '一次出多条不同角度的笔记，每条 6 张图 + 文案，可整包下载。'),
            h('div', { style: { height: 8 } }),
            h('label', { className: 'xhs-field' },
              h('span', { className: 'xhs-label' }, '出多少条'),
              h('select', { value: batchCount, onChange: (event) => setBatchCount(Number(event.target.value)) },
                [6, 12, 18, 24, 30].map((value) => h('option', { key: value, value }, `${value} 条`)))),
            h('div', { style: { height: 8 } }),
            h('button', {
              className: 'xhs-btn primary', style: { width: '100%', padding: 9 },
              disabled: running || !pack?.runId, onClick: runBatch,
            }, batch ? '重新批量出图' : `批量生成 ${batchCount} 条`))),
        mode === 'notes' && h(React.Fragment, null,
        h('section', { className: 'xhs-card' },
          h('h2', null, h('span', { className: 'xhs-step' }, '2'), '勾选选题', h('span', { className: 'state' }, analysis ? `${selectedCount}/${analysis.topics.length}` : '待提炼')),
          h('p', { style: { margin: 0, fontSize: 11.5, color: 'var(--muted)', lineHeight: 1.6 } },
            analysis ? '在右侧清单里勾选，标题和角度可以直接改。' : '先导入资料并提炼，选题会出现在右侧。')),
        h('section', { className: 'xhs-card' },
          h('h2', null, h('span', { className: 'xhs-step' }, '3'), '模板与出图'),
          h('label', { className: 'xhs-field' },
            h('span', { className: 'xhs-label' }, '写作模板 ', h('span', { className: 'xhs-hint' }, '技能')),
            h('select', { value: cfg.writing, onChange: (event) => setCfg({ ...cfg, writing: event.target.value }) },
              writingTemplates.map((template) => h('option', { key: template.id, value: template.id }, template.name)))),
          h('div', { className: 'xhs-row' },
            h('label', { className: 'xhs-field' },
              h('span', { className: 'xhs-label' }, '封面版式'),
              h('select', { value: cfg.cover, onChange: (event) => setCfg({ ...cfg, cover: event.target.value }) },
                Object.entries(env.catalog?.covers || { poster: '大字报' }).map(([id, label]) => h('option', { key: id, value: id }, label)))),
            h('label', { className: 'xhs-field' },
              h('span', { className: 'xhs-label' }, '内页版式'),
              h('select', { value: cfg.card, onChange: (event) => setCfg({ ...cfg, card: event.target.value }) },
                Object.entries(env.catalog?.cards || { index: '编号卡片' }).map(([id, label]) => h('option', { key: id, value: id }, label))))),
          h('div', { className: 'xhs-row' },
            h('label', { className: 'xhs-field' },
              h('span', { className: 'xhs-label' }, '配色'),
              h('select', { value: cfg.palette, onChange: (event) => setCfg({ ...cfg, palette: event.target.value }) },
                [['warm', '米白朱红'], ['paper', '暖纸棕'], ['mint', '浅绿'], ['ink', '深色金']].map(([id, label]) => h('option', { key: id, value: id }, label)))),
            h('label', { className: 'xhs-field' },
              h('span', { className: 'xhs-label' }, '内页张数'),
              h('select', { value: cfg.cards, onChange: (event) => setCfg({ ...cfg, cards: Number(event.target.value) }) },
                [2, 3, 4, 5, 6].map((value) => h('option', { key: value, value }, `${value} 张`))))),
          h('label', { className: 'xhs-field' },
            h('span', { className: 'xhs-label' }, '图上署名 ', h('span', { className: 'xhs-hint' }, '可留空')),
            h('input', { value: cfg.signature, maxLength: 24, placeholder: '不填就不显示', onChange: (event) => setCfg({ ...cfg, signature: event.target.value }) })),
          h('div', { style: { display: 'flex', gap: 7, marginTop: 4 } },
            h('button', { className: 'xhs-btn', style: { flex: 1 }, onClick: () => setDrawer(true) }, '模板管理'),
            h('button', { className: 'xhs-btn primary', style: { flex: 1.4, padding: 9 }, disabled: running || !selectedCount, onClick: generate },
              selectedCount ? `生成 ${selectedCount} 篇` : '生成'))),
        ),
      )

      const topicsView = analysis ? h('section', { className: 'xhs-panel' },
        h('div', { className: 'xhs-toolbar' },
          h('strong', null, `选题清单 · ${analysis.topics.length}`),
          h('span', { className: 'meta' }, `已选 ${selectedCount}`),
          h('span', { className: 'spacer' }),
          h('button', { className: 'xhs-btn ghost', onClick: () => setAll(true) }, '全选'),
          h('button', { className: 'xhs-btn ghost', onClick: () => setAll(false) }, '清空'),
          h('button', { className: 'xhs-btn', onClick: analyze, disabled: running || !files.length }, '换一批'),
          h('button', { className: 'xhs-btn primary', disabled: running || !selectedCount, onClick: generate }, `生成选中的 ${selectedCount} 篇`)),
        h('div', { className: 'xhs-topics' },
          analysis.topics.map((topic) => h('div', { className: `xhs-topic${topic.selected ? ' on' : ''}`, key: topic.id },
            h('div', { className: 'pick' },
              h('input', { type: 'checkbox', checked: Boolean(topic.selected), onChange: () => toggleTopic(topic.id) })),
            h('div', { className: 'main' },
              h('input', { className: 'title', value: topic.title, onChange: (event) => editTopic(topic.id, { title: event.target.value }) }),
              h('input', { className: 'angle', value: topic.angle || '', placeholder: '切入角度', onChange: (event) => editTopic(topic.id, { angle: event.target.value }) }),
              (topic.key_facts || []).length > 0 && h('div', { className: 'facts' }, topic.key_facts.join(' · '))),
            topic.source && h('span', { className: 'src', title: topic.source }, topic.source))))) : null

      const resultsView = result ? h('section', { className: 'xhs-panel' },
        h('div', { className: 'xhs-summary' },
          h('strong', null, `共 ${result.notes.length} 篇`),
          h('span', { className: 'meta' }, result.report?.elapsed_sec != null ? `用时 ${result.report.elapsed_sec}s` : ''),
          h('span', { className: 'meta' }, result.report?.template ? `${result.report.template.writing} · ${result.report.template.cover}/${result.report.template.card}` : ''),
          h('span', { className: 'spacer' }),
          h('a', { className: 'xhs-btn', href: result.indexUrl, download: `xhs-${result.runId}.xlsx` }, '总清单 xlsx'),
          h('a', { className: 'xhs-btn', href: result.zipUrl, download: `xhs-${result.runId}.zip` }, '打包下载'),
          h('button', { className: 'xhs-btn', onClick: reveal }, '打开文件夹'),
          h('button', { className: 'xhs-btn ghost', onClick: () => { setResult(null); setAnalysis(null) } }, '重新开始')),
        h('div', { className: 'xhs-grid' },
          result.notes.map((note, index) => h(NoteCard, {
            key: note.dir, note, onOpen: () => setPreview({ index, image: 0 }),
          })))) : null

      const activePlan = pack?.plans?.[packIndex] || null
      const packPreviewResult = batchPreview ? {
        notes: [{
          dir: `batch-${batchPreview.id}`,
          title: String(batchPreview.title).split('\n').join(' / '),
          caption: batchPreview.caption,
          images: batchPreview.images,
        }],
      } : packResult ? {
        notes: [{
          dir: 'pack',
          title: activePlan ? String(activePlan.title).split('\n').join(' / ') : '资料包笔记',
          caption: packResult.caption,
          images: packResult.images,
        }],
      } : null

      const packEmptyView = h('section', { className: 'xhs-panel' },
        h('div', { className: 'xhs-empty' },
          h('div', null,
            h('div', { className: 'ico' }, '▤'),
            h('h3', null, '拖资料 → 3 套方案 → 6 张图'),
            h('p', null, '资料包模式：表格 / 模板类资料自动解析，', h('br'), '模型给方案，固定版式出图。'),
            h('div', { className: 'xhs-steps' },
              h('span', null, '① 拖入资料'),
              h('span', null, '② 生成方案'),
              h('span', null, '③ 选一套出图')),
            h('p', { style: { marginTop: 12, fontSize: 11.5, color: 'var(--muted)' } },
              '不报份数、不带旧年份；同一套方案每次出图完全一样。'))))

      const packPlansView = pack ? h('section', { className: 'xhs-panel' },
        h('div', { className: 'xhs-toolbar' },
          h('strong', null, `${pack.plans.length} 套方案`),
          h('span', { className: 'meta' }, `${pack.files?.length || 0} 份资料 · 选一套出图`),
          h('span', { className: 'spacer' }),
          h('button', { className: 'xhs-btn ghost', disabled: running || !files.length, onClick: analyzePack }, '换一批')),
        h('div', { className: 'xhs-plans' },
          pack.plans.map((plan, index) => h('div', {
            className: `xhs-plan${index === packIndex ? ' on' : ''}`,
            key: index,
            onClick: () => setPackIndex(index),
          },
            h('div', { className: 'head' },
              h('span', { className: 'badge' }, `方案 ${index + 1}`),
              h('b', null, plan.name)),
            h('h4', null, String(plan.title || '').split('\n').join(' / ')),
            h('div', { className: 'aud' }, plan.audience || ''),
            h('div', { className: 'cats' },
              (plan.categories || []).map((item, i) => h('span', { key: i }, item.name))),
            h('div', { className: 'prev' },
              (plan.previews || []).map((item, i) => h('span', { key: i }, item.badge))),
            h('button', {
              className: `xhs-btn${index === packIndex ? ' primary' : ''}`,
              disabled: running,
              onClick: (event) => { event.stopPropagation(); generatePack(index) },
            }, '用这套出图'))))) : null

      const batchResultsView = batch ? h('section', { className: 'xhs-panel' },
        h('div', { className: 'xhs-toolbar' },
          h('strong', null, `批量结果 ${batch.count} 条`),
          h('span', { className: 'meta' }, '点封面看整套图和文案'),
          h('span', { className: 'spacer' }),
          h('a', { className: 'xhs-btn', href: batch.zipUrl, download: `pack-batch-${batch.runId}.zip` }, '打包下载全部'),
          h('button', { className: 'xhs-btn', onClick: revealPack }, '打开文件夹'),
          h('button', { className: 'xhs-btn ghost', disabled: running, onClick: runBatch }, '重新批量'),
          h('button', { className: 'xhs-btn ghost', onClick: () => setBatch(null) }, '返回单套')),
        h('div', { className: 'xhs-batch-grid' },
          batch.notes.map((note) => h('article', { className: 'xhs-batch-card', key: note.id },
            h('button', {
              className: 'cover',
              onClick: () => { setBatchPreview(note); setPreview({ index: 0, image: 0 }) },
            }, h('img', { src: note.images[0]?.url, alt: note.title, loading: 'lazy' })),
            h('h5', { title: note.title }, String(note.title).split('\n').join(' ')),
            h('p', null, note.audience),
            h('footer', null,
              h('span', null, `扣「${note.keyword || '资料'}」`),
              h('span', null, `${note.images.length} 图 · ${note.caption.length} 字`)))))) : null

      const packResultsView = packResult ? h('section', { className: 'xhs-panel' },
        h('div', { className: 'xhs-toolbar' },
          h('strong', null, activePlan ? String(activePlan.title).split('\n').join(' ') : '资料包笔记'),
          h('span', { className: 'meta' }, `${packResult.files?.length || 0} 份资料 · ${packResult.images.length} 张图`),
          h('span', { className: 'spacer' }),
          h('a', { className: 'xhs-btn', href: packResult.zipUrl, download: `pack-${packResult.runId}.zip` }, '打包下载'),
          h('button', { className: 'xhs-btn', onClick: revealPack }, '打开文件夹'),
          h('button', { className: 'xhs-btn', onClick: () => copyCaption(packResult.caption) }, '复制文案'),
          h('button', { className: 'xhs-btn ghost', onClick: () => setPackResult(null) }, '换一套')),
        h('div', { className: 'xhs-pack-body' },
          h('div', { className: 'xhs-pack-imgs' },
            packResult.images.map((image, index) => h('div', { className: 'xhs-pack-item', key: image.name },
              h('button', { onClick: () => setPreview({ index: 0, image: index }), title: image.name },
                h('img', { src: image.url, alt: image.name })),
              h('span', { className: 'lbl' },
                ['封面', '清单', '预览 1', '预览 2', '预览 3', '领取'][index] || image.name)))),
          h('div', { className: 'xhs-pack-doc' },
            h('h4', null, '笔记文案',
              h('button', {
                className: 'xhs-btn ghost', style: { marginLeft: 'auto', padding: '2px 8px', fontSize: 11 },
                onClick: () => copyCaption(packResult.caption),
              }, '复制'),
              h('span', null, `${packResult.caption.length} 字`)),
            h('pre', null, packResult.caption)))) : null

      const packView = batch ? batchResultsView : packResult ? packResultsView : pack ? packPlansView : packEmptyView

      const recentRuns = (env.runs || []).length > 0
        ? h('div', { className: 'xhs-recent' },
            h('h4', null, '最近的运行'),
            env.runs.slice(0, 4).map((run) => h('div', {
              className: 'row', key: run.runId, onClick: () => openHistory(run),
            },
              h('span', { className: 't' }, `${run.title || run.runId} · ${run.kind === 'batch' ? `${run.count} 条` : run.kind === 'pack' ? `${run.count} 张图` : `${run.notes} 篇`}`),
              h('span', { style: { color: '#c8193b' } }, '查看 ›'))))
        : null

      const emptyState = h('section', { className: 'xhs-panel' },
        h('div', { className: 'xhs-empty' },
          h('div', null,
            h('div', { className: 'ico' }, '✷'),
            h('h3', null, '资料 → 选题 → 内容'),
            h('p', null, '先把资料丢进来提炼选题，勾选你想写的那几个，', h('br'), '再按模板统一出图。版式固定，不靠抽卡。'),
            h('div', { className: 'xhs-steps' },
              h('span', null, '① 导入资料'),
              h('span', null, '② 勾选选题'),
              h('span', null, '③ 模板出图')),
            h('p', { style: { marginTop: 12, fontSize: 11.5, color: 'var(--muted)' } },
              '左侧「新会话」或右上角「对话」，都能把 AI 对话叫到右边。'),
            recentRuns)))

      const main = h('main', { className: 'xhs-main' },
        error ? h('div', { className: 'xhs-banner err', role: 'alert' },
          h('span', null, error),
          h('span', { className: 'spacer' }),
          h('button', { className: 'xhs-btn ghost', onClick: () => setError('') }, '知道了')) : null,
        !running && env.ready === false ? h('div', { className: 'xhs-banner warn' },
          h('span', null, '首次使用需要准备运行环境（Python 依赖 + 渲染器），大约 1-2 分钟。'),
          h('span', { className: 'spacer' }),
          h('button', { className: 'xhs-btn', onClick: prepareEnv }, '准备环境')) : null,
        running
          ? h(Progress, { job, onCancel: cancel })
          : mode === 'pack'
            ? packView
            : result
              ? resultsView
              : analysis
                ? topicsView
                : emptyState)

      return h('div', { className: chatOpen ? 'xhs-root chat' : 'xhs-root' },
        h('header', { className: 'xhs-bar' },
          h('div', { className: 'xhs-brand' },
            h('div', { className: 'xhs-logo' }, '薯'),
            h('div', null,
              h('h1', null, '小红书批量工作台'),
              h('p', null, '资料进 → 选题 → 模板化图文'))),
          h('div', { className: 'xhs-bar-actions' },
            envChip,
            offline && h('button', { className: 'xhs-btn', onClick: refreshEnv }, '重试'),
            h('button', {
              className: chatOpen ? 'xhs-btn primary' : 'xhs-btn',
              onClick: toggleChat, title: '在这个工作台里和 AI 对话',
            }, chatOpen ? '收起对话' : '对话'),
            h('button', { className: 'xhs-btn', onClick: () => setDrawer(true) }, '模板 / 技能'),
            h('button', { className: 'xhs-btn', onClick: () => setHistoryOpen(true), title: '历史生成的图文' },
              '历史', (env.runs || []).length ? h('span', { className: 'xhs-count' }, env.runs.length) : null),
            h('button', { className: 'xhs-btn', onClick: reveal, title: env.root || '' }, '输出目录'))),
        h('div', { className: 'xhs-body' }, side, main),
        historyOpen && h('div', { className: 'xhs-drawer-overlay', onClick: () => setHistoryOpen(false) },
          h('aside', { className: 'xhs-history', onClick: (event) => event.stopPropagation() },
            h('div', { className: 'xhs-history-head' },
              h('strong', null, '历史记录'),
              h('span', { className: 'spacer' }),
              h('span', { style: { fontSize: 11, color: 'var(--muted)' } }, `${(env.runs || []).length} 条`),
              h('button', { className: 'xhs-btn ghost', onClick: () => setHistoryOpen(false) }, '关闭')),
            (env.runs || []).length
              ? h('div', { className: 'xhs-history-list' },
                  env.runs.map((run) => h('button', {
                    key: run.runId, className: 'xhs-history-row', onClick: () => openHistory(run),
                  },
                    h('span', { className: 'thumb' },
                      run.thumb ? h('img', { src: run.thumb, alt: '' }) : h('span', { className: 'ph' }, run.kind === 'notes' ? '笔' : '包')),
                    h('span', { className: 'body' },
                      h('strong', null, run.title || `#${run.runId}`),
                      h('span', { className: 'meta' },
                        h('em', { className: `kind ${run.kind}` },
                          run.kind === 'batch' ? '批量' : run.kind === 'pack' ? '资料包' : '知识笔记'),
                        h('span', null, run.kind === 'batch' ? `${run.count} 条` : run.kind === 'pack' ? `${run.count} 张` : `${run.notes} 篇`),
                        h('span', null, run.when))),
                    h('span', { className: 'go' }, '打开'))))
              : h('p', { className: 'xhs-history-empty' }, '还没有历史记录，先出一套图试试。'))),
        chatOpen && h('aside', { className: 'xhs-chat' },
          h('div', { className: 'xhs-chat-head' },
            h('strong', null, 'AI 对话'),
            h('span', { className: 'spacer' }),
            h('button', { className: 'xhs-btn ghost', onClick: () => setChatOpen(false) }, '收起')),
          h('div', { className: 'xhs-chat-body' },
            hasSession
              ? conversation
              : h('div', { className: 'xhs-chat-empty' },
                  h('strong', null, chatBusy ? '正在打开对话…' : '这个工作台还没有对话'),
                  chatBusy ? '正在为当前工作区创建会话' : '创建后可以让我改选题、改文案、调模板。',
                  !chatBusy && h('div', { style: { marginTop: 10 } },
                    h('button', { className: 'xhs-btn primary', onClick: startConversation }, '开始对话'))))),
        preview && (mode === 'pack' ? packPreviewResult : result) && h(Preview, {
          result: mode === 'pack' ? packPreviewResult : result,
          index: preview.index,
          imageIndex: preview.image,
          onIndex: (index, image) => setPreview({ index, image }),
          onClose: () => { setPreview(null); setBatchPreview(null) },
          onToast: notify,
        }),
        drawer && h(TemplateDrawer, {
          catalog: env.catalog,
          onClose: () => setDrawer(false),
          onSave: saveTemplate,
          onDelete: deleteTemplate,
          notify,
        }),
        toast && h('div', { className: 'xhs-toast', role: 'status' }, toast))
    }

    class PanelGuard extends React.Component {
      constructor(props) {
        super(props)
        this.state = { error: '' }
      }
      static getDerivedStateFromError(error) {
        return { error: String((error && error.message) || error || '未知错误') }
      }
      componentDidCatch(error) {
        console.error('[xhs-batch] panel error:', error)
      }
      render() {
        if (!this.state.error) return this.props.children
        return h('div', { style: { padding: 24, fontFamily: '-apple-system,"PingFang SC",sans-serif', color: '#221a1e' } },
          h('h3', { style: { margin: '0 0 8px', fontSize: 15 } }, '工作台界面出错了'),
          h('pre', { style: { whiteSpace: 'pre-wrap', background: '#fff3f5', border: '1px solid #f5cdd6', color: '#ac1733', padding: 12, borderRadius: 10, fontSize: 12, lineHeight: 1.7 } }, this.state.error),
          h('button', {
            style: { marginTop: 10, border: '1px solid #ece2e6', background: '#fff', borderRadius: 8, padding: '6px 12px', cursor: 'pointer' },
            onClick: () => this.setState({ error: '' }),
          }, '重试'))
      }
    }

    function GuardedPanel(props) {
      return h(PanelGuard, null, h(Panel, props))
    }

    function apply(ctx) {
      ctx.effect(() => ctx.desktopWorkbenches.register({
        title: '小红书批量工作台',
        description: '资料提炼选题 → 勾选 → 按模板批量生成小红书图文，版式固定可复用。',
        category: '内容创作',
        panelTitle: '小红书批量工作台',
        icon: '薯',
        audience: '内容创作者 / 博主',
        repository: 'https://github.com/local/xhs-batch-studio',
        customFrame: true,
      }, GuardedPanel))
    }

    return { apply, inject: ['desktopWorkbenches'] }
  },
})
