export const COLORS = {
  brandGreen: "#A8D75A",
  brandOrange: "#F39C12",
  good: "#27AE60",
  goodLight: "#2ECC71",
  bad: "#E74C3C",
  warn: "#F39C12",
  target: "#42A5F5",
  neutralBar: "#5B8DEF",
  // Priority palette (matches the PDF)
  priority: {
    Critical: "#E74C3C",
    Major: "#F39C12",
    Minor: "#F1C40F",
    None: "#5DADE2",
  },
};

export const PRIORITY_ORDER = ["Critical", "Major", "Minor", "None"];

// Business spec: SLA% counts Critical + Major jobs only. Page "KPI SLA % Per Team" is
// the exception — it follows whatever priorities the user picked in the filter bar.
export const SLA_PRIORITIES = new Set(["Critical", "Major"]);

// The zone every company's unmatched jobs fall into (server/companies.py OTHER_ZONE).
export const OTHER_ZONE = "อื่นๆ";

export const MONTHS_EN = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export const MONTHS_TH = [
  "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
  "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
];

export const ZONE_PALETTE = [
  "#3498DB", "#9B59B6", "#16A085", "#E67E22", "#2C3E50", "#C0392B", "#7F8C8D", "#27AE60",
];

// Line colours for "per team" charts. The first three keep the PDF's A=red,
// B=yellow, C=green convention; companies with more teams continue the palette.
export const TEAM_PALETTE = [
  "#E74C3C", "#F1C40F", "#27AE60", "#3498DB", "#9B59B6", "#E67E22", "#1ABC9C",
  "#34495E", "#D35400", "#8E44AD", "#2ECC71", "#C0392B", "#16A085", "#7F8C8D",
];

export const pick = (palette, i) => palette[((i % palette.length) + palette.length) % palette.length];
