package com.gathin.tvhome;

import android.app.Activity;
import android.content.*;
import android.graphics.*;
import android.graphics.drawable.*;
import android.os.*;
import android.util.TypedValue;
import android.view.*;
import android.widget.*;
import java.text.SimpleDateFormat;
import java.util.*;

public final class LiquidGlassLockEngine {
    private static final long FRAME_MS = 33L; // Strict 30 FPS pacing for Mi TV 4A Pro (1GB RAM)
    private static final long IDLE_MS = 180000L; // 3 minutes idle auto-lock
    private static LiquidGlassLockEngine inst;
    private final Activity act;
    private final Handler h = new Handler(Looper.getMainLooper());
    private FrameLayout lockView;
    private ImageView wpView;
    private TextView greetTv, clockTv, dateTv;
    private boolean locked = true, anim = false;
    private int curPeriod = -1;
    private View lastFocus;
    private final WeakHashMap<View, Boolean> styled = new WeakHashMap<>();
    private final Runnable idleTask = () -> { if (!locked && !act.isFinishing()) animateLock(true); };

    private LiquidGlassLockEngine(Activity a) { this.act = a; }

    public static void attach(Activity a) {
        inst = new LiquidGlassLockEngine(a);
        a.getWindow().getDecorView().post(() -> { if (!a.isFinishing()) inst.init(); });
    }

    public static void onStart(Activity a) {
        if (inst != null && inst.act == a && inst.lockView != null) inst.lockNow();
    }

    public static boolean onKey(Activity a, KeyEvent e) {
        return inst != null && inst.act == a && inst.handleKey(e);
    }

    private void init() {
        ViewGroup root = act.findViewById(android.R.id.content);
        if (root == null) return;
        root.setBackground(new BitmapDrawable(act.getResources(), renderWallpaper(4)));
        root.getViewTreeObserver().addOnGlobalLayoutListener(() -> {
            if (root.getChildCount() > 0) styleTree(root.getChildAt(0));
        });
        root.getViewTreeObserver().addOnGlobalFocusChangeListener((oldV, newV) -> {
            if (oldV != null && oldV != lockView) {
                styleTile(oldV, false);
                scale30Fps(oldV, oldV.getScaleX(), 1.0f);
            }
            if (newV != null && newV != lockView && !locked) {
                lastFocus = newV;
                styleTile(newV, true);
                scale30Fps(newV, newV.getScaleX(), 1.10f);
            }
        });
        buildLockUI(root);
        updateClock(true);
        lockNow();
        IntentFilter f = new IntentFilter(Intent.ACTION_TIME_TICK);
        f.addAction(Intent.ACTION_TIME_CHANGED);
        f.addAction(Intent.ACTION_SCREEN_ON);
        act.registerReceiver(new BroadcastReceiver() {
            @Override public void onReceive(Context c, Intent i) {
                if (Intent.ACTION_SCREEN_ON.equals(i.getAction())) lockNow();
                else updateClock(false);
            }
        }, f);
    }

    private void styleTree(View v) {
        if (v == null || v == lockView) return;
        if (v.isFocusable() && !styled.containsKey(v)) {
            styled.put(v, true);
            styleTile(v, v.hasFocus());
        }
        if (v instanceof ViewGroup) {
            ViewGroup vg = (ViewGroup) v;
            for (int i = 0; i < vg.getChildCount(); i++) styleTree(vg.getChildAt(i));
        }
    }

    private void styleTile(View v, boolean focus) {
        GradientDrawable g = new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,
            focus ? new int[]{0x58FFFFFF, 0x26FFFFFF, 0x3890CAF9} : new int[]{0x24FFFFFF, 0x12FFFFFF});
        g.setCornerRadius(dp(18));
        g.setStroke(dp(focus ? 2 : 1), focus ? 0xEEFFFFFF : 0x44FFFFFF);
        v.setBackground(g);
        v.setElevation(dp(focus ? 12 : 2));
    }

    private void buildLockUI(ViewGroup root) {
        lockView = new FrameLayout(act);
        wpView = new ImageView(act);
        wpView.setScaleType(ImageView.ScaleType.CENTER_CROP);
        lockView.addView(wpView, -1, -1);

        LinearLayout hud = new LinearLayout(act);
        hud.setOrientation(LinearLayout.VERTICAL);
        hud.setGravity(Gravity.CENTER_HORIZONTAL);
        FrameLayout.LayoutParams hLp = new FrameLayout.LayoutParams(-2, -2, Gravity.TOP | Gravity.CENTER_HORIZONTAL);
        hLp.topMargin = Math.max(dp(64), (int)(act.getResources().getDisplayMetrics().heightPixels * 0.13f));

        Typeface tf = Typeface.create("sans-serif-light", Typeface.NORMAL);
        greetTv = new TextView(act);
        greetTv.setTypeface(tf);
        greetTv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 20);
        greetTv.setTextColor(0xF5FFFFFF);
        greetTv.setPadding(dp(22), dp(7), dp(22), dp(7));
        styleTile(greetTv, false);
        hud.addView(greetTv);

        clockTv = new TextView(act);
        clockTv.setTypeface(tf);
        clockTv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 76);
        clockTv.setTextColor(Color.WHITE);
        clockTv.setShadowLayer(16f, 0f, 5f, 0x99000000);
        hud.addView(clockTv);

        dateTv = new TextView(act);
        dateTv.setTypeface(tf);
        dateTv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        dateTv.setTextColor(0xE0FFFFFF);
        hud.addView(dateTv);
        lockView.addView(hud, hLp);

        TextView pill = new TextView(act);
        pill.setText("Press OK to Unlock");
        pill.setTypeface(tf);
        pill.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        pill.setTextColor(Color.WHITE);
        pill.setPadding(dp(28), dp(11), dp(28), dp(11));
        styleTile(pill, true);
        FrameLayout.LayoutParams pLp = new FrameLayout.LayoutParams(-2, -2, Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
        pLp.bottomMargin = dp(44);
        lockView.addView(pill, pLp);
        root.addView(lockView, -1, -1);
    }

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
