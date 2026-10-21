export const STYLES = `
:host { all: initial; --ma-primary: #c2410c; --ma-on-primary: #fff; --ma-accent: #1f2937; --ma-radius: 16px;
  font-family: "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif; color: #111827; }
*, *::before, *::after { box-sizing: border-box; }
button { font: inherit; cursor: pointer; }
.launcher { position: fixed; bottom: 20px; right: 20px; z-index: 2147483000; display: flex; align-items: center; gap: 8px;
  border: 0; border-radius: 999px; padding: 12px 18px 12px 14px; background: var(--ma-primary); color: var(--ma-on-primary);
  font-size: 15px; font-weight: 700; box-shadow: 0 10px 30px rgba(0,0,0,.25); transition: transform .15s ease; }
.launcher:hover { transform: translateY(-2px); }
.launcher svg { width: 24px; height: 24px; }
:host([data-position="left"]) .launcher, :host([data-position="left"]) .panel { right: auto; left: 20px; }
.panel { position: fixed; bottom: 20px; right: 20px; z-index: 2147483001; width: 400px; height: min(680px, calc(100vh - 40px));
  display: flex; flex-direction: column; background: #fff; border-radius: var(--ma-radius); overflow: hidden;
  box-shadow: 0 24px 60px rgba(0,0,0,.28); border: 1px solid #e5e7eb; }
.panel[hidden], .launcher[hidden] { display: none; }
header { display: flex; align-items: center; gap: 10px; padding: 14px 16px; background: var(--ma-primary); color: var(--ma-on-primary); }
header img { width: 34px; height: 34px; border-radius: 10px; background: #fff; }
header .titles { flex: 1; min-width: 0; line-height: 1.2; }
header .name { font-weight: 700; font-size: 15px; }
header .sub { font-size: 12px; opacity: .9; }
header button { border: 0; background: rgba(255,255,255,.16); color: inherit; border-radius: 10px; padding: 6px 10px; font-size: 13px; }
header button.icon { width: 34px; height: 34px; padding: 0; display: grid; place-items: center; }
.messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; background: #f8fafc; }
.msg { max-width: 88%; padding: 10px 13px; border-radius: 14px; font-size: 14px; line-height: 1.5; word-wrap: break-word; }
.msg p { margin: 0 0 6px; } .msg p:last-child { margin-bottom: 0; }
.msg ul, .msg ol { margin: 4px 0 6px; padding-left: 20px; } .msg li { margin: 2px 0; }
.msg.user { align-self: flex-end; background: var(--ma-accent); color: #fff; border-bottom-right-radius: 4px; }
.msg.bot { align-self: flex-start; background: #fff; border: 1px solid #e5e7eb; border-bottom-left-radius: 4px; }
.msg.error { align-self: center; background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; font-size: 13px; }
.msg.system { align-self: center; background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; font-size: 13px; }
.sku { display: inline-block; font-size: 11px; font-weight: 600; padding: 0 6px; border-radius: 6px; background: #f1f5f9; color: #334155; }
.typing { display: inline-flex; gap: 4px; padding: 4px 0; } .typing i { width: 6px; height: 6px; border-radius: 50%; background: #94a3b8; animation: b 1s infinite; }
.typing i:nth-child(2) { animation-delay: .15s } .typing i:nth-child(3) { animation-delay: .3s }
@keyframes b { 0%,80%,100% { opacity: .3 } 40% { opacity: 1 } }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { border: 1px solid #e2e8f0; background: #fff; color: #0f172a; border-radius: 999px; padding: 7px 12px; font-size: 13px; text-align: left; }
.chip:hover { border-color: var(--ma-primary); }
.cards { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 4px; scroll-snap-type: x mandatory; }
.card { flex: 0 0 168px; scroll-snap-align: start; background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; }
.card img { width: 100%; aspect-ratio: 1; object-fit: cover; background: #f1f5f9; display: block; }
.card .body { padding: 8px 10px 10px; display: flex; flex-direction: column; gap: 4px; flex: 1; }
.card a.t { font-size: 12.5px; line-height: 1.35; color: #111827; text-decoration: none; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 34px; }
.card .reason { font-size: 11px; color: #475569; }
.price { font-weight: 800; font-size: 14px; } .old { font-size: 11px; color: #64748b; text-decoration: line-through; margin-right: 4px; font-weight: 400; }
.btn { border: 0; border-radius: 10px; padding: 8px 10px; font-size: 13px; font-weight: 700; background: var(--ma-primary); color: var(--ma-on-primary); }
.btn.secondary { background: #fff; color: #0f172a; border: 1px solid #cbd5e1; }
.btn:disabled { opacity: .6; cursor: default; }
.btn.done { background: #15803d; color: #fff; }
.bundle { background: #fff; border: 2px solid var(--ma-primary); border-radius: 14px; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
.bundle h4 { margin: 0; font-size: 14px; } .bundle .why { font-size: 12px; color: #475569; margin: 0; }
.bundle ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.bundle li { display: flex; align-items: center; gap: 8px; font-size: 12.5px; }
.bundle li img { width: 36px; height: 36px; border-radius: 8px; object-fit: cover; flex: none; }
.bundle li span.n { flex: 1; } .bundle li .role { font-size: 10px; font-weight: 700; color: var(--ma-primary); text-transform: uppercase; }
.bundle .total { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e5e7eb; padding-top: 8px; font-size: 13px; }
.sources { display: flex; flex-wrap: wrap; gap: 6px; }
.source { font-size: 11.5px; color: #1e3a8a; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 999px; padding: 3px 9px; text-decoration: none; }
.feedback { display: flex; gap: 6px; margin-top: -4px; }
.feedback button { border: 1px solid #e2e8f0; background: #fff; border-radius: 8px; width: 30px; height: 26px; font-size: 13px; color: #334155; }
.feedback button[aria-pressed="true"] { background: var(--ma-primary); color: var(--ma-on-primary); border-color: var(--ma-primary); }
form.composer { display: flex; gap: 8px; padding: 10px 12px; border-top: 1px solid #e5e7eb; background: #fff; }
form.composer textarea { flex: 1; resize: none; border: 1px solid #cbd5e1; border-radius: 12px; padding: 10px 12px; font: inherit; font-size: 14px; max-height: 110px; color: #111827; }
form.composer textarea:focus, .quote input:focus, .quote textarea:focus { outline: 2px solid var(--ma-primary); outline-offset: 1px; }
form.composer button { width: 44px; border-radius: 12px; border: 0; background: var(--ma-primary); color: var(--ma-on-primary); display: grid; place-items: center; }
form.composer button svg { width: 20px; height: 20px; }
.disclaimer { font-size: 11px; color: #64748b; text-align: center; padding: 0 12px 8px; background: #fff; margin: 0; }
.quote { background: #fff; border: 1px solid #e5e7eb; border-radius: 14px; padding: 12px; display: grid; gap: 8px; }
.quote h4 { margin: 0; font-size: 14px; }
.quote label { display: grid; gap: 3px; font-size: 12px; font-weight: 600; color: #334155; }
.quote input, .quote textarea { border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px; font: inherit; font-size: 13px; color: #111827; }
.quote .row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.quote .items { font-size: 12px; color: #334155; margin: 0; padding-left: 16px; }
.quote .actions { display: flex; gap: 8px; justify-content: flex-end; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
@media (max-width: 640px) {
  .panel { inset: 0; width: 100%; height: 100%; max-height: none; border-radius: 0; border: 0; bottom: 0; right: 0; }
  :host([data-position="left"]) .panel { left: 0; }
  .launcher { bottom: 14px; right: 14px; }
}
@media (prefers-reduced-motion: reduce) { .launcher, .typing i { transition: none; animation: none; } }
`;
