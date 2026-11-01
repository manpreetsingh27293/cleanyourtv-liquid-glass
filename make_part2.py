import pathlib, re

main_file = next(pathlib.Path("/data/data/com.termux/files/home/cleanyourtv-work/launcher").rglob("MainActivity.java"))
engine_file = main_file.parent / "LiquidGlassLockEngine.java"

part2_code = """
    private void updateClock(boolean force) {
        if (clockTv == null) return;
        Date now = new Date();
        clockTv.setText(new SimpleDateFormat("h:mm", Locale.getDefault()).format(now));
        dateTv.setText(new SimpleDateFormat("EEEE, MMMM d", Locale.getDefault()).format(now));
        int hr = Calendar.getInstance().get(Calendar.HOUR_OF_DAY);
        int p = (hr >= 5 && hr < 12) ? 0 : (hr >= 12 && hr < 17) ? 1 : (hr >= 17 && hr < 20) ? 2 : 3;
        String[] greets = {"Good Morning", "Good Afternoon", "Good Evening", "Good Night"};
        greetTv.setText(greets[p]);
        if (force || p != curPeriod) {
            curPeriod = p;
            wpView.setImageBitmap(renderWallpaper(p));
        }
    }

    private Bitmap renderWallpaper(int mode) {
        int W = 1280, H = 720;
        Bitmap bmp = Bitmap.createBitmap(W, H, Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(bmp);
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        int[][] skies = {
            {0xFF1C2A58, 0xFF705280, 0xFFEE8A5C, 0xFFFFD287},
            {0xFF0C3E8A, 0xFF2484D6, 0xFF6ECDF5, 0xFFC8F0FF},
            {0xFF121034, 0xFF4E1C58, 0xFFC03A4E, 0xFFFA8E40},
            {0xFF050816, 0xFF0C1630, 0xFF142C4E, 0xFF0C182E},
            {0xFF080C1C, 0xFF101836, 0xFF161032, 0xFF060A16}
        };
        p.setShader(new LinearGradient(0, 0, 0, H, skies[mode], null, Shader.TileMode.CLAMP));
        c.drawRect(0, 0, W, H, p);

        int[] orbX = {920, 640, 380, 980, 320};
        int[] orbY = {400, 160, 430, 190, 220};
        int[] orbCol = {0xCCFFEBAA, 0x99FFFFFF, 0xCCFFA550, 0x8820D2A5, 0x883880FF};
        p.setShader(new RadialGradient(orbX[mode], orbY[mode], 340, orbCol[mode], 0x00000000, Shader.TileMode.CLAMP));
        c.drawRect(0, 0, W, H, p);

        if (mode == 4) {
            p.setShader(new RadialGradient(980, 260, 360, 0x80A840FF, 0x00000000, Shader.TileMode.CLAMP));
            c.drawRect(0, 0, W, H, p);
            return bmp;
        }
        int[] mCols = {0xCC281E44, 0xE618122C, 0xFF0E0A1C};
        for (int r = 0; r < 3; r++) {
            Path path = new Path();
            float base = H * (0.66f + r * 0.09f);
            path.moveTo(0, H);
            for (int x = 0; x <= W; x += 64) {
                float y = base + (float)Math.sin(x * 0.006 + r * 2.1 + mode) * (38 - r * 8);
                path.lineTo(x, y);
            }
            path.lineTo(W, H);
            path.close();
            p.setShader(null);
            p.setColor(mCols[r]);
            c.drawPath(path, p);
        }
        return bmp;
    }

    private boolean handleKey(KeyEvent e) {
        int k = e.getKeyCode();
        if (k == KeyEvent.KEYCODE_VOLUME_UP || k == KeyEvent.KEYCODE_VOLUME_DOWN || k == KeyEvent.KEYCODE_VOLUME_MUTE) return false;
        if (locked) {
            if (e.getAction() == KeyEvent.ACTION_DOWN && !anim && (k == KeyEvent.KEYCODE_DPAD_CENTER || k == KeyEvent.KEYCODE_ENTER)) {
                animateLock(false);
            }
            return true;
        }
        h.removeCallbacks(idleTask);
        h.postDelayed(idleTask, IDLE_MS);
        if (k == KeyEvent.KEYCODE_BACK && e.getAction() == KeyEvent.ACTION_DOWN && e.getRepeatCount() >= 1 && !anim) {
            animateLock(true);
            return true;
        }
        return false;
    }

    private void lockNow() {
        h.removeCallbacks(idleTask);
        updateClock(false);
        locked = true;
        anim = false;
        lockView.setVisibility(View.VISIBLE);
        lockView.setAlpha(1f);
        lockView.setScaleX(1f);
        lockView.setScaleY(1f);
    }

    private void animateLock(boolean toLock) {
        anim = true;
        locked = toLock;
        if (toLock) {
            updateClock(false);
            lockView.setAlpha(0f);
            lockView.setVisibility(View.VISIBLE);
        }
        long st = SystemClock.uptimeMillis();
        h.post(new Runnable() {
            @Override public void run() {
                float t = Math.min(1f, (SystemClock.uptimeMillis() - st) / 330f);
                float ease = 1f - (float)Math.pow(1f - t, 3);
                lockView.setAlpha(toLock ? ease : (1f - ease));
                float sc = toLock ? (1.06f - 0.06f * ease) : (1f + 0.08f * ease);
                lockView.setScaleX(sc);
                lockView.setScaleY(sc);
                if (t < 1f) h.postDelayed(this, FRAME_MS);
                else {
                    anim = false;
                    if (!toLock) {
                        lockView.setVisibility(View.GONE);
                        if (lastFocus != null) lastFocus.requestFocus();
                        h.postDelayed(idleTask, IDLE_MS);
                    }
                }
            }
        });
    }

    private void scale30Fps(View v, float s0, float s1) {
        long st = SystemClock.uptimeMillis();
        h.post(new Runnable() {
            @Override public void run() {
                float t = Math.min(1f, (SystemClock.uptimeMillis() - st) / 198f);
                float cur = s0 + (s1 - s0) * (1f - (float)Math.pow(1f - t, 3));
                v.setScaleX(cur);
                v.setScaleY(cur);
                if (t < 1f) h.postDelayed(this, FRAME_MS);
            }
        });
    }

    private int dp(int v) { return Math.round(v * act.getResources().getDisplayMetrics().density); }
}
"""
with open(engine_file, "a") as f:
    f.write(part2_code)

code = main_file.read_text()
code = re.sub(r'(super\.onCreate\([^)]*\)\s*;)', r'\1\n        LiquidGlassLockEngine.attach(this);', code, count=1)
last_b = code.rfind("}")
code = code[:last_b] + """
    @Override protected void onStart() { super.onStart(); LiquidGlassLockEngine.onStart(this); }
    @Override public boolean dispatchKeyEvent(android.view.KeyEvent e) {
        if (LiquidGlassLockEngine.onKey(this, e)) return true;
        return super.dispatchKeyEvent(e);
    }
}
"""
main_file.write_text(code)
print("PART 2 SAVED!")
