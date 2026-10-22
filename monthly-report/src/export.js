import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import PptxGenJS from "pptxgenjs";

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

// Wait for any Recharts wrappers on the page to actually render bars/paths
// before screenshotting. Falls back after `timeoutMs`.
async function waitForCharts(timeoutMs = 6000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const wrappers = document.querySelectorAll(".recharts-wrapper");
    if (wrappers.length === 0) {
      // No charts on this page -> nothing to wait for
      await wait(120);
      return;
    }
    const allReady = Array.from(wrappers).every(
      (w) => w.querySelectorAll("path, rect, .recharts-pie-sector").length > 0
    );
    if (allReady) {
      // Settle one more animation frame
      await wait(220);
      return;
    }
    await wait(120);
  }
}

// Capture the export target inside the active page area.
// Returns { dataUrl, width, height } in image pixels (deviceScaleFactor applied).
async function captureCurrentPage(targetEl) {
  const scale = 2; // 2x for crisper output
  const canvas = await html2canvas(targetEl, {
    scale,
    backgroundColor: "#ffffff",
    useCORS: true,
    logging: false,
    windowWidth: document.documentElement.clientWidth,
  });
  return {
    dataUrl: canvas.toDataURL("image/png"),
    width: canvas.width,
    height: canvas.height,
  };
}

// Iterate through every page in NAV, switch to it, wait for render, capture.
// `onProgress` receives (i, total, currentPageName).
export async function captureAllPages({ nav, setActiveId, getTargetEl, onProgress }) {
  const shots = [];
  for (let i = 0; i < nav.length; i++) {
    const it = nav[i];
    onProgress?.(i, nav.length, it.t);
    setActiveId(it.id);
    // wait for React render + Recharts paint
    await wait(350);
    await waitForCharts();
    const target = getTargetEl();
    if (!target) continue;
    const shot = await captureCurrentPage(target);
    shots.push({ ...shot, title: it.t, num: it.n });
  }
  onProgress?.(nav.length, nav.length, "done");
  return shots;
}

export async function exportToPDF(shots, { filename = "Monthly-Report.pdf", title = "Monthly Report" } = {}) {
  if (!shots.length) throw new Error("ไม่พบหน้ารายงานให้ export");
  // Landscape A4 in mm: 297 x 210
  const pdf = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
  const pageW = pdf.internal.pageSize.getWidth();
  const pageH = pdf.internal.pageSize.getHeight();
  pdf.setProperties({ title });
  for (let i = 0; i < shots.length; i++) {
    const s = shots[i];
    if (i > 0) pdf.addPage();
    // Fit image into page preserving aspect ratio
    const ratio = s.width / s.height;
    const pageRatio = pageW / pageH;
    let drawW, drawH;
    if (ratio > pageRatio) {
      drawW = pageW - 8;
      drawH = drawW / ratio;
    } else {
      drawH = pageH - 8;
      drawW = drawH * ratio;
    }
    const x = (pageW - drawW) / 2;
    const y = (pageH - drawH) / 2;
    pdf.addImage(s.dataUrl, "PNG", x, y, drawW, drawH, undefined, "FAST");
  }
  pdf.save(filename);
}

export async function exportToPPTX(shots, { filename = "Monthly-Report.pptx", title = "Monthly Report" } = {}) {
  if (!shots.length) throw new Error("ไม่พบหน้ารายงานให้ export");
  const pptx = new PptxGenJS();
  pptx.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
  pptx.title = title;
  pptx.author = title;
  const slideW = 13.33;
  const slideH = 7.5;

  for (const s of shots) {
    const slide = pptx.addSlide();
    slide.background = { color: "F5F6F8" };
    // Fit image preserving aspect ratio inside slide bounds
    const ratio = s.width / s.height;
    const pageRatio = slideW / slideH;
    let drawW, drawH;
    if (ratio > pageRatio) {
      drawW = slideW - 0.3;
      drawH = drawW / ratio;
    } else {
      drawH = slideH - 0.3;
      drawW = drawH * ratio;
    }
    const x = (slideW - drawW) / 2;
    const y = (slideH - drawH) / 2;
    slide.addImage({ data: s.dataUrl, x, y, w: drawW, h: drawH });
  }
  await pptx.writeFile({ fileName: filename });
}
