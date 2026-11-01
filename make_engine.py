import pathlib, re

main_file = next(pathlib.Path("/data/data/com.termux/files/home/cleanyourtv-work/launcher").rglob("MainActivity.java"))
pkg_match = re.search(r"package\s+([\w\.]+);", main_file.read_text())
pkg_name = pkg_match.group(1)
engine_file = main_file.parent / "LiquidGlassLockEngine.java"

engine_code = """package PKG_REPLACE;

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
    private static final long FRAME_MS = 33L;
    private static final long IDLE_MS = 180000L;
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
"""
engine_file.write_text(engine_code.replace("PKG_REPLACE", pkg_name))
print("PART 1 SAVED!")
