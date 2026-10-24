#!/usr/bin/env python3
# AnfiGram patch: applied in CI before the build. Run from the repo root.
import pathlib
import re
import sys

ROOT = pathlib.Path(".")
JAVA = ROOT / "TMessagesProj/src/main/java/org/telegram"


def read(p):
    return p.read_text(encoding="utf-8")


def write(p, s):
    p.write_text(s, encoding="utf-8")


def replace_once(path, old, new):
    s = read(path)
    if s.count(old) != 1:
        sys.exit("PATCH FAILED in %s: anchor found %d times:\n%s" % (path, s.count(old), old))
    write(path, s.replace(old, new))


# ---------------------------------------------------------------- new files
ANFI_CONFIG = r'''package org.telegram.messenger;

import android.content.Context;
import android.content.SharedPreferences;

public class AnfiConfig {

    private static volatile Boolean showSeconds;

    private static SharedPreferences prefs() {
        return ApplicationLoader.applicationContext.getSharedPreferences("anfigram", Context.MODE_PRIVATE);
    }

    public static boolean isShowSeconds() {
        Boolean value = showSeconds;
        if (value == null) {
            if (ApplicationLoader.applicationContext == null) {
                return false;
            }
            value = prefs().getBoolean("show_seconds", false);
            showSeconds = value;
        }
        return value;
    }

    public static void setShowSeconds(boolean value) {
        showSeconds = value;
        prefs().edit().putBoolean("show_seconds", value).apply();
    }
}
'''

ANFI_SETTINGS = r'''package org.telegram.ui;

import android.content.Context;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;

import org.telegram.messenger.AnfiConfig;
import org.telegram.messenger.R;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Cells.TextCheckCell;
import org.telegram.ui.Cells.TextInfoPrivacyCell;
import org.telegram.ui.Components.LayoutHelper;

public class AnfiSettingsActivity extends BaseFragment {

    @Override
    public View createView(Context context) {
        actionBar.setBackButtonImage(R.drawable.ic_ab_back);
        actionBar.setAllowOverlayTitle(true);
        actionBar.setTitle("Настройки AnfiGram");
        actionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() {
            @Override
            public void onItemClick(int id) {
                if (id == -1) {
                    finishFragment();
                }
            }
        });

        FrameLayout frameLayout = new FrameLayout(context);
        fragmentView = frameLayout;
        frameLayout.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundGray));

        ScrollView scrollView = new ScrollView(context);
        LinearLayout list = new LinearLayout(context);
        list.setOrientation(LinearLayout.VERTICAL);
        scrollView.addView(list, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT));
        frameLayout.addView(scrollView, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.MATCH_PARENT));

        final TextCheckCell secondsCell = new TextCheckCell(context);
        secondsCell.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));
        secondsCell.setTextAndCheck("Секунды во времени сообщений", AnfiConfig.isShowSeconds(), false);
        secondsCell.setOnClickListener(v -> {
            boolean enabled = !AnfiConfig.isShowSeconds();
            AnfiConfig.setShowSeconds(enabled);
            secondsCell.setChecked(enabled);
        });
        list.addView(secondsCell, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        TextInfoPrivacyCell info = new TextInfoPrivacyCell(context);
        info.setText("Вместо ЧЧ:ММ время показывается как ЧЧ:ММ:СС. Чтобы изменения применились, закройте и снова откройте чат.");
        list.addView(info, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        return fragmentView;
    }
}
'''

write(JAVA / "messenger/AnfiConfig.java", ANFI_CONFIG)
write(JAVA / "ui/AnfiSettingsActivity.java", ANFI_SETTINGS)

# ------------------------------------------------- seconds in message time
replace_once(
    JAVA / "messenger/LocaleController.java",
    "    public FastDateFormat getFormatterDay() {\n        if (formatterDay == null) {",
    "    public FastDateFormat getFormatterDay() {\n"
    "        if (AnfiConfig.isShowSeconds()) {\n"
    "            return getFormatterDayWithSeconds();\n"
    "        }\n"
    "        if (formatterDay == null) {",
)

# --------------------------------------------- menu entry in main settings
settings = JAVA / "ui/SettingsActivity.java"
replace_once(
    settings,
    "        items.add(UItem.asHeader(getString(R.string.SettingsHelp)));",
    "        items.add(SettingCell.Factory.of(30, IconBackgroundColors.CYAN.top, IconBackgroundColors.CYAN.bottom, R.drawable.settings_features, \"Настройки AnfiGram\", \"Секунды во времени и другое\"));\n"
    "        items.add(UItem.asShadow(null));\n"
    "        items.add(UItem.asHeader(getString(R.string.SettingsHelp)));",
)
replace_once(
    settings,
    "            case 17:\n                showDialog(AlertsCreator.createSupportAlert(this, resourceProvider));",
    "            case 30:\n                presentSettingFragment(new AnfiSettingsActivity());\n                break;\n"
    "            case 17:\n                showDialog(AlertsCreator.createSupportAlert(this, resourceProvider));",
)

# ------------------------------------------------------------- app name
strings = ROOT / "TMessagesProj/src/main/res/values/strings.xml"
s = read(strings)
s, n1 = re.subn(r'(<string name="AppName">)[^<]*(</string>)', r"\1AnfiGram\2", s)
s, n2 = re.subn(r'(<string name="AppNameBeta">)[^<]*(</string>)', r"\1AnfiGram\2", s)
if n1 != 1 or n2 != 1:
    sys.exit("PATCH FAILED: app name strings (%d, %d)" % (n1, n2))
write(strings, s)

# ---------------------------------------------------------- package name
NEW_PKG = "com.anfigram.app"
replace_once(ROOT / "gradle.properties", "APP_PACKAGE=org.telegram.messenger", "APP_PACKAGE=" + NEW_PKG)
for gs in (ROOT / "TMessagesProj_App/google-services.json", ROOT / "TMessagesProj/google-services.json"):
    if gs.exists():
        t = read(gs)
        t, n = re.subn(r'"package_name":\s*"org\.telegram\.messenger', '"package_name": "' + NEW_PKG, t)
        if n == 0:
            sys.exit("PATCH FAILED: no package_name in %s" % gs)
        write(gs, t)

print("AnfiGram patch applied")
