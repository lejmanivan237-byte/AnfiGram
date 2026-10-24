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

import org.telegram.tgnet.TLRPC;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.Set;

public class AnfiConfig {

    private static final int MAX_DELETED = 5000;

    private static volatile Boolean showSeconds;
    private static volatile Boolean keepDeleted;
    private static volatile Boolean showProfileId;
    private static LinkedHashSet<String> deletedIds;

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

    public static boolean isKeepDeleted() {
        Boolean value = keepDeleted;
        if (value == null) {
            if (ApplicationLoader.applicationContext == null) {
                return false;
            }
            value = prefs().getBoolean("keep_deleted", true);
            keepDeleted = value;
        }
        return value;
    }

    public static void setKeepDeleted(boolean value) {
        keepDeleted = value;
        prefs().edit().putBoolean("keep_deleted", value).apply();
    }

    public static boolean isShowProfileId() {
        Boolean value = showProfileId;
        if (value == null) {
            if (ApplicationLoader.applicationContext == null) {
                return false;
            }
            value = prefs().getBoolean("show_profile_id", true);
            showProfileId = value;
        }
        return value;
    }

    public static void setShowProfileId(boolean value) {
        showProfileId = value;
        prefs().edit().putBoolean("show_profile_id", value).apply();
    }

    private static synchronized LinkedHashSet<String> deleted() {
        if (deletedIds == null) {
            deletedIds = new LinkedHashSet<>();
            if (ApplicationLoader.applicationContext != null) {
                Set<String> saved = prefs().getStringSet("deleted_ids", null);
                if (saved != null) {
                    deletedIds.addAll(saved);
                }
            }
        }
        return deletedIds;
    }

    // key: 0 for private chats and basic groups, -channelId for channels and supergroups
    public static synchronized void markDeleted(long key, ArrayList<Integer> ids) {
        if (ids == null || ids.isEmpty() || ApplicationLoader.applicationContext == null) {
            return;
        }
        LinkedHashSet<String> set = deleted();
        for (int i = 0; i < ids.size(); i++) {
            set.add(key + "_" + ids.get(i));
        }
        while (set.size() > MAX_DELETED) {
            String first = set.iterator().next();
            set.remove(first);
        }
        prefs().edit().putStringSet("deleted_ids", new HashSet<>(set)).apply();
    }

    public static synchronized boolean isMarkedDeleted(TLRPC.Message message) {
        if (message == null || message.id <= 0) {
            return false;
        }
        long channelId = message.peer_id != null ? message.peer_id.channel_id : 0;
        long key = channelId != 0 ? -channelId : 0;
        return deleted().contains(key + "_" + message.id);
    }

    public static String profileId(long userId, long chatId, boolean channel) {
        if (userId != 0) {
            return String.valueOf(userId);
        }
        if (chatId == 0) {
            return "";
        }
        return channel ? "-100" + chatId : "-" + chatId;
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

    private interface Getter {
        boolean get();
    }

    private interface Setter {
        void set(boolean value);
    }

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

        addToggle(context, list, "Секунды во времени сообщений",
                "Вместо ЧЧ:ММ время показывается как ЧЧ:ММ:СС. Чтобы изменения применились, закройте и снова откройте чат.",
                AnfiConfig::isShowSeconds, AnfiConfig::setShowSeconds);

        addToggle(context, list, "Сохранять удалённые сообщения",
                "Сообщения, которые удалил собеседник, остаются в чате с пометкой «удалено». Сохраняются только те сообщения, которые приложение уже получило. Удаление, сделанное вами, работает как обычно.",
                AnfiConfig::isKeepDeleted, AnfiConfig::setKeepDeleted);

        addToggle(context, list, "Показывать ID в профиле",
                "В профиле пользователя, группы или канала появляется строка с ID. Нажмите на неё, чтобы скопировать. Откройте профиль заново, чтобы увидеть изменение.",
                AnfiConfig::isShowProfileId, AnfiConfig::setShowProfileId);

        return fragmentView;
    }

    private void addToggle(Context context, LinearLayout list, String title, String info, Getter getter, Setter setter) {
        final TextCheckCell cell = new TextCheckCell(context);
        cell.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));
        cell.setTextAndCheck(title, getter.get(), false);
        cell.setOnClickListener(v -> {
            boolean enabled = !getter.get();
            setter.set(enabled);
            cell.setChecked(enabled);
        });
        list.addView(cell, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        TextInfoPrivacyCell infoCell = new TextInfoPrivacyCell(context);
        infoCell.setText(info);
        list.addView(infoCell, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));
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
    "        items.add(SettingCell.Factory.of(30, IconBackgroundColors.CYAN.top, IconBackgroundColors.CYAN.bottom, R.drawable.settings_features, \"Настройки AnfiGram\", \"Секунды, удалённые сообщения, ID\"));\n"
    "        items.add(UItem.asShadow(null));\n"
    "        items.add(UItem.asHeader(getString(R.string.SettingsHelp)));",
)
replace_once(
    settings,
    "            case 17:\n                showDialog(AlertsCreator.createSupportAlert(this, resourceProvider));",
    "            case 30:\n                presentSettingFragment(new AnfiSettingsActivity());\n                break;\n"
    "            case 17:\n                showDialog(AlertsCreator.createSupportAlert(this, resourceProvider));",
)

# --------------------------------------------- keep messages deleted by others
mc = JAVA / "messenger/MessagesController.java"
replace_once(
    mc,
    "        LongSparseArray<ArrayList<Integer>> deletedMessagesFinal = deletedMessages;\n",
    "        if (AnfiConfig.isKeepDeleted() && deletedMessages != null) {\n"
    "            for (int anfiI = 0; anfiI < deletedMessages.size(); anfiI++) {\n"
    "                AnfiConfig.markDeleted(deletedMessages.keyAt(anfiI), deletedMessages.valueAt(anfiI));\n"
    "            }\n"
    "            deletedMessages = null;\n"
    "        }\n"
    "        LongSparseArray<ArrayList<Integer>> deletedMessagesFinal = deletedMessages;\n",
)
replace_once(
    mc,
    "    protected void deleteMessagesByPush(long dialogId, ArrayList<Integer> ids, long channelId) {\n",
    "    protected void deleteMessagesByPush(long dialogId, ArrayList<Integer> ids, long channelId) {\n"
    "        if (AnfiConfig.isKeepDeleted()) {\n"
    "            AnfiConfig.markDeleted(channelId == 0 ? 0 : -channelId, ids);\n"
    "            getMessagesStorage().getStorageQueue().postRunnable(() -> getMessagesStorage().deletePushMessages(dialogId, ids));\n"
    "            return;\n"
    "        }\n",
)

# label "deleted" next to the message time
replace_once(
    ROOT / "TMessagesProj/src/main/java/org/telegram/ui/Cells/ChatMessageCell.java",
    "        if (currentMessageObject.messageOwner.video_processing_pending) {\n"
    "            timeString = formatString(R.string.ScheduledTimeApprox, timeString);\n"
    "        }\n"
    "        if (signString != null) {",
    "        if (currentMessageObject.messageOwner.video_processing_pending) {\n"
    "            timeString = formatString(R.string.ScheduledTimeApprox, timeString);\n"
    "        }\n"
    "        if (timeString != null && timeString.length() > 0 && org.telegram.messenger.AnfiConfig.isMarkedDeleted(currentMessageObject.messageOwner)) {\n"
    "            timeString = \"удалено · \" + timeString;\n"
    "        }\n"
    "        if (signString != null) {",
)

# ------------------------------------------------------------- ID in profile
pa = JAVA / "ui/ProfileActivity.java"
replace_once(pa, "    private int usernameRow;\n", "    private int usernameRow;\n    private int anfiIdRow;\n")
replace_once(pa, "        usernameRow = -1;\n", "        usernameRow = -1;\n        anfiIdRow = -1;\n")
replace_once(
    pa,
    "                infoStartRow = rowCount;\n                if (!isBot && (hasPhone || !hasInfo)) {",
    "                infoStartRow = rowCount;\n"
    "                if (AnfiConfig.isShowProfileId()) {\n"
    "                    anfiIdRow = rowCount++;\n"
    "                }\n"
    "                if (!isBot && (hasPhone || !hasInfo)) {",
)
replace_once(
    pa,
    "                if (ChatObject.isPublic(currentChat)) {\n                    usernameRow = rowCount++;\n                }",
    "                if (AnfiConfig.isShowProfileId()) {\n"
    "                    anfiIdRow = rowCount++;\n"
    "                }\n"
    "                if (ChatObject.isPublic(currentChat)) {\n                    usernameRow = rowCount++;\n                }",
)
replace_once(
    pa,
    "                    } else if (position == phoneRow) {\n                        String text;\n                        TLRPC.User user = getMessagesController().getUser(userId);",
    "                    } else if (position == anfiIdRow) {\n"
    "                        detailCell.setTextAndValue(AnfiConfig.profileId(userId, chatId, ChatObject.isChannel(currentChat)), \"ID (нажмите, чтобы скопировать)\", false);\n"
    "                    } else if (position == phoneRow) {\n                        String text;\n                        TLRPC.User user = getMessagesController().getUser(userId);",
)
replace_once(
    pa,
    "            } else if (position == usernameRow) {\n                processOnClickOrPress(position, view, x, y);",
    "            } else if (position == anfiIdRow) {\n"
    "                AndroidUtilities.addToClipboard(AnfiConfig.profileId(userId, chatId, ChatObject.isChannel(currentChat)));\n"
    "                BulletinFactory.of(this).createCopyBulletin(\"ID скопирован\", resourcesProvider).show();\n"
    "            } else if (position == usernameRow) {\n                processOnClickOrPress(position, view, x, y);",
)
replace_once(
    pa,
    "            } else if (position == phoneRow || position == locationRow || position == numberRow || position == birthdayRow) {\n                return VIEW_TYPE_TEXT_DETAIL;",
    "            } else if (position == anfiIdRow || position == phoneRow || position == locationRow || position == numberRow || position == birthdayRow) {\n                return VIEW_TYPE_TEXT_DETAIL;",
)
replace_once(
    pa,
    "            put(++pointer, usernameRow, sparseIntArray);\n",
    "            put(++pointer, anfiIdRow, sparseIntArray);\n            put(++pointer, usernameRow, sparseIntArray);\n",
)
# ProfileActivity lives in org.telegram.ui, AnfiConfig in org.telegram.messenger
s = read(pa)
if "import org.telegram.messenger.AnfiConfig;" not in s:
    s = s.replace("import org.telegram.messenger.AndroidUtilities;", "import org.telegram.messenger.AndroidUtilities;\nimport org.telegram.messenger.AnfiConfig;", 1)
    if "import org.telegram.messenger.AnfiConfig;" not in s:
        sys.exit("PATCH FAILED: could not add AnfiConfig import to ProfileActivity")
    write(pa, s)

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
