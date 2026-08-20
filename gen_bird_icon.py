import zlib, struct

def make_png(path, size):
    W = H = size
    r = int(size * 0.22)          # 背景圆角
    px = [[(0,0,0,0) for _ in range(W)] for _ in range(H)]

    def setp(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            px[y][x] = c

    def inside_round(x, y, x0, y0, x1, y1, rad):
        if x < x0 or x >= x1 or y < y0 or y >= y1:
            return False
        cx = [x0+rad, x1-rad, x0+rad, x1-rad]
        cy = [y0+rad, y0+rad, y1-rad, y1-rad]
        for (ccx, ccy) in zip(cx, cy):
            if (x0+rad <= x <= x1-rad) or (y0+rad <= y <= y1-rad):
                continue
            if (x-ccx)**2 + (y-ccy)**2 > rad*rad:
                return False
        return True

    def fill_round_rect(x0,y0,x1,y1,rad,color):
        for y in range(y0, y1):
            for x in range(x0, x1):
                if inside_round(x, y, x0, y0, x1, y1, rad):
                    setp(x, y, color)

    def fill_circle(cx, cy, rad, color):
        for y in range(int(cy-rad), int(cy+rad)+1):
            for x in range(int(cx-rad), int(cx+rad)+1):
                if (x-cx)**2 + (y-cy)**2 <= rad*rad:
                    setp(x, y, color)

    def fill_ellipse(cx, cy, rx, ry, color):
        for y in range(int(cy-ry), int(cy+ry)+1):
            for x in range(int(cx-rx), int(cx+rx)+1):
                if ((x-cx)/rx)**2 + ((y-cy)/ry)**2 <= 1:
                    setp(x, y, color)

    def fill_triangle(p1, p2, p3, color):
        xs = [p1[0],p2[0],p3[0]]; ys=[p1[1],p2[1],p3[1]]
        minx,maxx = int(min(xs)), int(max(xs))+1
        miny,maxy = int(min(ys)), int(max(ys))+1
        def sign(a,b,c):
            return (a[0]-c[0])*(b[1]-c[1]) - (b[0]-c[0])*(a[1]-c[1])
        for y in range(miny, maxy):
            for x in range(minx, maxx):
                pt=(x,y)
                d1=sign(pt,p1,p2); d2=sign(pt,p2,p3); d3=sign(pt,p3,p1)
                if (d1>=0)==(d2>=0)==(d3>=0):
                    setp(x,y,color)

    # 背景：天空渐变（与游戏一致）
    bg0 = (78, 192, 202)    # #4ec0ca
    bg1 = (155, 231, 214)   # #9be7d6
    for y in range(H):
        for x in range(W):
            t = y / H
            c = tuple(int(bg0[i]*(1-t) + bg1[i]*t) for i in range(3)) + (255,)
            if inside_round(x, y, 0, 0, W, H, r):
                setp(x, y, c)

    # 小鸟：黄色身体（带深色描边）
    cx, cy = size*0.50, size*0.54
    br = size*0.30
    fill_circle(cx, cy, br+size*0.02, (120, 90, 0, 255))          # 描边
    fill_circle(cx, cy, br, (255, 211, 61, 255))                  # 身体

    # 翅膀
    fill_ellipse(cx - size*0.10, cy + size*0.04, size*0.15, size*0.11, (247, 181, 0, 255))

    # 眼睛（白底黑瞳）
    ex, ey = cx + size*0.12, cy - size*0.10
    fill_circle(ex, ey, size*0.085, (255,255,255,255))
    fill_circle(ex + size*0.015, ey, size*0.04, (0,0,0,255))

    # 嘴（橙三角，朝右）
    bx = cx + br - size*0.02
    fill_triangle((bx, cy - size*0.02),
                  (bx + size*0.16, cy - size*0.05),
                  (bx, cy + size*0.06), (255, 122, 0, 255))

    # 头顶呆毛
    fill_triangle((cx, cy - br - size*0.04),
                  (cx - size*0.03, cy - br - size*0.12),
                  (cx + size*0.03, cy - br - size*0.12), (247, 181, 0, 255))

    # 编码 PNG
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        for x in range(W):
            raw += bytes(px[y][x])
    comp = zlib.compress(bytes(raw), 9)
    def chunk(typ, data):
        return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", zlib.crc32(typ+data) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    print("wrote", path, size, "x", size)

make_png("C:/html/Bird/icon-512.png", 512)
make_png("C:/html/Bird/icon-192.png", 192)
