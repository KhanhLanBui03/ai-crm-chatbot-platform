// [PRODUCTION] CSS của widget — nằm TRONG Shadow DOM nên không rò ra trang chủ nhà và không bị
// CSS của trang chủ nhà làm vỡ. Màu chủ đạo là DỮ LIỆU doanh nghiệp chọn (UC009), truyền vào
// qua biến --mau.

export const CSS = `
:host { all: initial; }
* { box-sizing: border-box; font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
.goc { position: fixed; bottom: 20px; z-index: 2147483000; display: flex; flex-direction: column; gap: 12px; }
.goc.phai { right: 20px; align-items: flex-end; }
.goc.trai { left: 20px; align-items: flex-start; }

.bong { width: 56px; height: 56px; border-radius: 50%; border: none; cursor: pointer;
  background: var(--mau); color: #fff; box-shadow: 0 6px 20px rgba(0,0,0,.2);
  display: flex; align-items: center; justify-content: center; }
.bong:focus-visible, button:focus-visible, textarea:focus-visible { outline: 3px solid rgba(0,0,0,.35); outline-offset: 2px; }
.bong svg { width: 26px; height: 26px; }

.khung { width: min(370px, calc(100vw - 40px)); height: min(560px, calc(100vh - 110px));
  background: #fff; color: #1f2937; border-radius: 14px; box-shadow: 0 12px 40px rgba(0,0,0,.22);
  display: flex; flex-direction: column; overflow: hidden; font-size: 14px; }
.khung[hidden] { display: none; }

.dau { background: var(--mau); color: #fff; padding: 12px 14px; display: flex; align-items: center; gap: 10px; }
.dau img { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; background: rgba(255,255,255,.3); }
.dau .ten { font-weight: 600; flex: 1; }
.dau button { background: transparent; border: none; color: #fff; cursor: pointer; font-size: 20px; line-height: 1; padding: 4px; }

.than { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 8px; background: #f7f7f9; }
.tin { max-width: 85%; padding: 8px 11px; border-radius: 12px; line-height: 1.45; white-space: pre-wrap; word-wrap: break-word; }
.tin.khach { align-self: flex-end; background: var(--mau); color: #fff; border-bottom-right-radius: 4px; }
.tin.bot, .tin.nv { align-self: flex-start; background: #fff; border: 1px solid #e5e7eb; border-bottom-left-radius: 4px; }
.tin.he-thong { align-self: center; background: #eef2ff; color: #3730a3; font-size: 12.5px; text-align: center; max-width: 95%; }
.nhan { font-size: 11px; color: #6b7280; margin-bottom: 2px; }
.nguon { margin-top: 6px; padding-top: 6px; border-top: 1px dashed #e5e7eb; font-size: 12px; color: #4b5563; }
.nguon b { font-weight: 600; }
.dang-go { align-self: flex-start; color: #6b7280; font-size: 12.5px; font-style: italic; }

.loi { margin: 0 14px 8px; padding: 8px 10px; border-radius: 8px; background: #fef2f2; color: #991b1b; font-size: 12.5px; }
.loi[hidden] { display: none; }

.chan { border-top: 1px solid #e5e7eb; padding: 10px; display: flex; flex-direction: column; gap: 8px; background: #fff; }
.chan .hang { display: flex; gap: 8px; align-items: flex-end; }
.chan textarea { flex: 1; resize: none; border: 1px solid #d1d5db; border-radius: 10px; padding: 8px 10px;
  font-size: 14px; max-height: 110px; min-height: 38px; }
.chan .gui { background: var(--mau); color: #fff; border: none; border-radius: 10px; padding: 0 14px; height: 38px; cursor: pointer; font-weight: 600; }
.chan .gui:disabled { opacity: .5; cursor: default; }
.chan .phu { display: flex; justify-content: space-between; align-items: center; font-size: 11.5px; color: #6b7280; }
.chan .gap-nv { background: none; border: none; color: #374151; text-decoration: underline; cursor: pointer; font-size: 12px; padding: 0; }
.chan .gap-nv[hidden] { display: none; }

.chan .nut { display: flex; gap: 12px; }
.chan .gap-nv[hidden] { display: none; }
.the-tt { align-self: stretch; background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px;
  display: flex; flex-direction: column; gap: 8px; }
.the-tt .tieu-de { font-weight: 600; font-size: 13.5px; }
.the-tt input[type=text], .the-tt input[type=tel], .the-tt input[type=email] { border: 1px solid #d1d5db;
  border-radius: 8px; padding: 7px 9px; font-size: 13.5px; width: 100%; }
.the-tt .dong-y { font-size: 12.5px; color: #374151; line-height: 1.4; display: flex; gap: 6px; align-items: flex-start; }
.the-tt .dong-y input { margin-top: 2px; }
.the-tt .loi-tt { color: #991b1b; font-size: 12.5px; }
.the-tt .loi-tt[hidden] { display: none; }
.the-tt .hang-nut { display: flex; justify-content: flex-end; gap: 8px; }
.the-tt .gui { background: var(--mau); color: #fff; border: none; border-radius: 8px; padding: 7px 14px; cursor: pointer; font-weight: 600; }
.the-tt .gui:disabled { opacity: .5; cursor: default; }
.the-tt .de-sau { background: none; border: none; color: #6b7280; cursor: pointer; font-size: 12.5px; }

.tam-ngung { padding: 24px 18px; text-align: center; color: #4b5563; line-height: 1.5; }
`
