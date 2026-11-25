# GrabCut each place inside its hand-set box -> clean mask. usage: python trace_map.py map.jpg out_dir
import sys, os, json, cv2, numpy as np
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
img = cv2.imread(src)
H, W = img.shape[:2]
# id: (x0, y0, x1, y1) boxes on the 2576x1438 map (buildings / plots)
BOX = json.load(open(os.path.join(os.path.dirname(__file__), "map_boxes.json")))
res = {}
for pid, (x0, y0, x1, y1) in BOX.items():
    pad = 40
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
    crop = img[Y0:Y1, X0:X1].copy()
    mask = np.full(crop.shape[:2], cv2.GC_BGD, np.uint8)
    rx0, ry0, rx1, ry1 = x0 - X0, y0 - Y0, x1 - X0, y1 - Y0
    mask[ry0:ry1, rx0:rx1] = cv2.GC_PR_FGD
    # sure foreground: an inner core
    cx0, cy0 = rx0 + (rx1 - rx0) * 3 // 10, ry0 + (ry1 - ry0) * 3 // 10
    cx1, cy1 = rx1 - (rx1 - rx0) * 3 // 10, ry1 - (ry1 - ry0) * 3 // 10
    mask[cy0:cy1, cx0:cx1] = cv2.GC_FGD
    bg = np.zeros((1, 65), np.float64); fg = np.zeros((1, 65), np.float64)
    cv2.grabCut(crop, mask, None, bg, fg, 6, cv2.GC_INIT_WITH_MASK)
    m = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    # clean: close holes, keep the biggest blob, smooth
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
    if n > 1:
        k = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA]); m = np.where(lab == k, 255, 0).astype(np.uint8)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    m2 = np.zeros_like(m); cv2.drawContours(m2, cnts, -1, 255, -1)
    m2 = cv2.GaussianBlur(m2, (0, 0), 3); m2 = np.where(m2 > 127, 255, 0).astype(np.uint8)
    full = np.zeros((H, W), np.uint8); full[Y0:Y1, X0:X1] = m2
    cv2.imwrite(os.path.join(out, "m_%s.png" % pid), full)
    res[pid] = int(full.sum() / 255)
print(res)
