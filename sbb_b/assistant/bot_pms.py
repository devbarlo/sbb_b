import re
from collections import defaultdict
from datetime import datetime
from typing import Optional, Union

import heroku3
from telethon import Button, events
from telethon.errors import UserIsBlockedError
from telethon.events import CallbackQuery, StopPropagation
from telethon.utils import get_display_name

from sbb_b import Config, sbb_b

from ..core import check_owner, pool
from ..core.logger import logging
from ..core.session import tgbot
from ..helpers import reply_id
from ..helpers.utils import _format
from ..sql_helper.bot_blacklists import check_is_black_list
from ..sql_helper.bot_pms_sql import (
    add_user_to_db,
    get_user_id,
    get_user_logging,
    get_user_reply,
)
from ..sql_helper.bot_starters import add_starter_to_db, get_starter_details
from ..sql_helper.globals import delgvar, gvarstatus
from . import BOTLOG, BOTLOG_CHATID
from .botmanagers import ban_user_from_bot

LOGS = logging.getLogger(__name__)

plugin_category = "bot"
botusername = Config.TG_BOT_USERNAME
Heroku = heroku3.from_key(Config.HEROKU_API_KEY)


class FloodConfig:
    BANNED_USERS = set()
    USERS = defaultdict(list)
    MESSAGES = 3
    SECONDS = 6
    ALERT = defaultdict(dict)
    AUTOBAN = 10


async def check_bot_started_users(user, event):
    if user.id == Config.OWNER_ID:
        return
    check = get_starter_details(user.id)
    if check is None:
        start_date = str(datetime.now().strftime("%B %d, %Y"))
        notification = f"👤 مستخدم جديد: {_format.mentionuser(user.first_name , user.id)}\
                \n**الايدي: **`{user.id}`\
                \n**الاسم: **{get_display_name(user)}"
    else:
        start_date = check.date
        notification = f"👤 المستخدم: {_format.mentionuser(user.first_name , user.id)}\
                \n**الايدي: **`{user.id}`\
                \n**الاسم: **{get_display_name(user)}"
    try:
        add_starter_to_db(user.id, get_display_name(user), start_date, user.username)
    except Exception as e:
        LOGS.error(str(e))
    if BOTLOG:
        await event.client.send_message(BOTLOG_CHATID, notification)


@sbb_b.bot_cmd(
    pattern=f"^/start({botusername})?([\s]+)?$",
    incoming=True,
    func=lambda e: e.is_private,
)
async def bot_start(event):
    chat = await event.get_chat()
    user = await sbb_b.get_me()
    if check_is_black_list(chat.id):
        return
    reply_to = await reply_id(event)
    mention = f"[{chat.first_name}](tg://user?id={chat.id})"
    my_mention = f"[{user.first_name}](tg://user?id={user.id})"
    first = chat.first_name
    last = chat.last_name
    fullname = f"{first} {last}" if last else first
    username = f"@{chat.username}" if chat.username else mention
    userid = chat.id
    my_first = user.first_name
    my_last = user.last_name
    my_fullname = f"{my_first} {my_last}" if my_last else my_first
    my_username = f"@{user.username}" if user.username else my_mention
    custompic = gvarstatus("BOT_START_PIC") or None
    if chat.id != Config.OWNER_ID:
        customstrmsg = gvarstatus("START_TEXT") or None
        if customstrmsg is not None:
            start_msg = customstrmsg.format(
                mention=mention,
                first=first,
                last=last,
                fullname=fullname,
                username=username,
                userid=userid,
                my_first=my_first,
                my_last=my_last,
                my_fullname=my_fullname,
                my_username=my_username,
                my_mention=my_mention,
            )
        else:
            start_msg = f"اهلا 👤{mention},\
                        \nانا هو البوت المساعد الخاص ل{my_mention} \
                        \nيمكنك التواصل مع ي من خلال هذا البوت"
        buttons = [
            (
                Button.url("السورس", "https://t.me/cr_source"),
                Button.url(
                    "المطور",
                    "https://t.me/wjj_u",
                ),
            )
        ]
    else:
        start_msg = "**اهلا بك عزيزي مالك البوت هذه هي اعدادات البوت الخاصة بك**"
        buttons = [
            [
                Button.url("• السورس •", "https://t.me/cr_source"),
                Button.inline("• الفارات •", data="setting"),
            ],
            [
                Button.inline("• اوامر البوت •", data="CMDBOT"),
                Button.inline("• اوامر المشغل •", data="MSHKLMSIC"),
            ],
        ]
    try:
        if custompic:
            await event.client.send_file(
                chat.id,
                file=custompic,
                caption=start_msg,
                link_preview=False,
                buttons=buttons,
                reply_to=reply_to,
            )
        else:
            await event.client.send_message(
                chat.id,
                start_msg,
                link_preview=False,
                buttons=buttons,
                reply_to=reply_to,
            )
    except Exception as e:
        if BOTLOG:
            await event.client.send_message(
                BOTLOG_CHATID,
                f"**خطأ**\nحدث خطأ ما اثناء تشغيل البوت الخاص بك\\\x1f                \n`{e}`",
            )

    else:
        await check_bot_started_users(chat, event)


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"MSHKLMSIC")))
async def varssett(event):
    await event.edit(
        "من هنا يمكنك عرض اوامر المشغل:",
        buttons=[
            [
                Button.inline("تشغيل المكالمة", data="rozlve"),
                Button.inline("انهاء المكالمة", data="endcalrz"),
                Button.inline("تسمية المكالمة", data="title_roz"),
            ],
            [
                Button.inline("دعوة للمكالمة", data="inv_vcrz"),
                Button.inline("معلومات المكالمة", data="info_roz"),
                Button.inline("انضمام للمكالمة", data="joinVoicecharoz"),
            ],
            [
                Button.inline("مغادرة المكالمة", data="leaveVoicechatroz"),
                Button.inline("قائمة التشغيل", data="get_playlistroz"),
                Button.inline("تشغيل فيديو", data="play_vide"),
            ],
            [
                Button.inline("تشغيل صوتي", data="play_audioroze"),
                Button.inline("ايقاف مؤقت", data="pause_streamroz"),
                Button.inline("تخطي التشغيل", data="skip_srazan"),
            ],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"skip_srazan")))
async def skip_srazan(event):
    await event.edit(
        """القسم: اوامر المشغل
الامر:       `.تخطي_التشغيل `

الشرح: يستخدم هذا الامر لتخطي التشغيل الحالي ويقوم بتشغيل المقطع الذي بعده بحسب قائمة التشغيل
ألاستخدام: اكتب الامر في الدردشة فقط

ملاحظة : يجب عليك ان تكون مفعل فار الميوزك اولا  الشرح  ~ اضغط هنا
قناة سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="MSHKLMSIC")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"resume_stzrzo")))
async def resume_stzrzo(event):
    await event.edit(
        """القسم: اوامر المشغل
الامر:       `.استئناف_التشغيل `

الشرح: يستخدم هذا الامر لأستئناف التشغيل في المكالمة
ألاستخدام: اكتب الامر في الدردشة فقط

ملاحظة : يجب عليك ان تكون مفعل فار الميوزك اولا  الشرح  ~ اضغط هنا
قناة سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="MSHKLMSIC")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"pause_streamroz")))
async def pause_streamroz(event):
    await event.edit(
        """القسم: اوامر المشغل
الامر:       `.ايقاف_مؤقت `

الشرح: يستخدم هذا الامر لايقاف التشغيل الحالية بشكل مؤقت في المكالمة
ألاستخدام: اكتب الامر في الدردشة فقط

ملاحظة : يجب عليك ان تكون مفعل فار الميوزك اولا  الشرح  ~ اضغط هنا
قناة سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="MSHKLMSIC")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"play_audioroze")))
async def play_vide(event):
    await event.edit(
        """القسم: اوامر المشغل
الامر:       `.تشغيل_صوتي `

الشرح: يستخدم هذا الامر لتشغيل المقطع الصوتي في المكالمة الصوتية
ألاستخدام: اكتب الامر مع رابط الفيديو من اليوتيوب

ملاحظة : يجب عليك ان تكون مفعل فار الميوزك اولا  الشرح  ~ اضغط هنا
قناة سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="MSHKLMSIC")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"play_vide")))
async def play_vide(event):
    await event.edit(
        """القسم: اوامر المشغل
الامر:       `.تشغيل_فيديو`

الشرح: يستخدم هذا الامر لتشغيل فيديو في المكالمة الصوتية
ألاستخدام: اكتب الامر مع رابط الفيديو من اليوتيوب

ملاحظة : يجب عليك ان تكون مفعل فار الميوزك اولا  الشرح  ~ اضغط هنا
قناة سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="MSHKLMSIC")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"get_playlistroz")))
async def get_playlistroz(event):
    await event.edit(
        """القسم: اوامر المشغل
الامر:       `.قائمة_التشغيل`

الشرح: يستخدم هذا الامر لمعرفة الفيديوهات والصوتيات المشغلة في المكالمة او في قائمة الانتظار
ألاستخدام: اكتب الامر فقط في الدردشة 

ملاحظة : يجب عليك ان تكون مفعل فار الميوزك اولا  الشرح  ~ اضغط هنا
قناة سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="MSHKLMSIC")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"leaveVoicechatroz")))
async def leaveVoicechat(event):
    await event.edit(
        """القسم: اوامر المشغل
الامر:       `.مغادرة_المكالمة`

الشرح: يستخدم هذا الامر لجعل البوت الذي بحسابك يغادر المكالمة الصوتية
ألاستخدام: اكتب الامر فقط في الدردشة 

ملاحظة : يجب عليك ان تكون مفعل فار الميوزك اولا  الشرح  ~ اضغط هنا
قناة سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="MSHKLMSIC")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"joinVoicecharoz")))
async def joinVoicecharoz(event):
    await event.edit(
        """القسم: اوامر المشغل
الامر:       `.انضمام_للمكالمة`

الشرح: يستخدم هذا الامر لجعل البوت الذي بحسابك يشغل و يدخل الى المكالمة الصوتية
ألاستخدام: اكتب الامر فقط في الدردشة 

ملاحظة : يجب عليك ان تكون مفعل فار الميوزك اولا  الشرح  ~ اضغط هنا
قناة سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="MSHKLMSIC")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"title_roz")))
async def title_v(event):
    await event.edit(
        """القسم: اوامر المشغل
الامر:       `.تسمية_المكالمة`

الشرح: يستخدم هذا الامر لتغيير اسم عنوان المكالمة الصوتية
ألاستخدام: اكتب الامر مع العنوان الجديد و ارسله في الدردشة

ملاحظة : يجب عليك ان تكون مفعل فار الميوزك اولا  الشرح  ~ اضغط هنا
قناة سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="MSHKLMSIC")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"info_roz")))
async def info_vc(event):
    await event.edit(
        """القسم: اوامر المشغل
الامر:       `.معلومات_المكالمة`

الشرح: يستخدم هذا الامر لمعرفة معلومات المكالمة من اسم و عدد والى اخره ..... 
ألاستخدام: اكتب الامر في المجموعة فقط ويجب ان تكون المكالمة شغالة

ملاحظة : يجب عليك ان تكون مفعل فار الميوزك اولا  الشرح  ~ اضغط هنا
قناة سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="MSHKLMSIC")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"inv_vcrz")))
async def varssett(event):
    await event.edit(
        """القسم: اوامر المشغل
الامر:       `.دعوة`

الشرح: يستخدم هذا الامر لدعوة المستخدم الى المكالمة الصوتية في المجموعة 
ألاستخدام: اكتب الامر بالرد على المستخدم الذي تريد دعوته للمكالمة

ملاحظة : يجب عليك ان تكون مفعل فار الميوزك اولا  الشرح  ~ اضغط هنا
قناة سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="MSHKLMSIC")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"rozlve")))
async def varssett(event):
    await event.edit(
        """القسم: اوامر المشغل
الامر:       `.تشغيل_المكالمة`

الشرح: يستخدم هذا الامر لتشغيل المكالمة الصوتية في المجموعة فقط ارسله في المجموعة ويجب ان تكون مشرف اولا
ألاستخدام: فقط ارسل الامر بدون اي اضافات

ملاحظة : يجب عليك ان تكون مفعل فار الميوزك اولا  الشرح  ~ اضغط هنا
قناة سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="MSHKLMSIC")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"endcalrz")))
async def varssett(event):
    await event.edit(
        """القسم: اوامر المشغل
الامر:       `.انهاء_المكالمة`

الشرح: يستخدم هذا الامر لانهاء المكالمة الصوتية في المجموعة فقط ارسله في المجموعة ويجب ان تكون مشرف اولا
ألاستخدام: فقط ارسل الامر بدون اي اضافات

ملاحظة : يجب عليك ان تكون مفعل فار الميوزك اولا  الشرح  ~ اضغط هنا
قناة سورس كرستين  @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="MSHKLMSIC")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"setting")))
async def varssett(event):
    await event.edit(
        "من هنا يمكنك عرض شروحات الفارات:",
        buttons=[
            [
                Button.inline("فارات الفحص", data="alivevar"),
                Button.inline("فارات الحماية", data="pmvars"),
            ],
            [Button.inline("فارات البروفايل", data="namevar")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"namevar")))
async def varssett(event):
    await event.edit(
        "من هنا يمكنك عرض شروحات فارات الاسم والبايو والخ:",
        buttons=[
            [
                Button.inline("اسم حسابك", data="nameprvr"),
                Button.inline("زخرفة الارقام", data="numlokvar"),
            ],
            [
                Button.inline("نبذة حسابك", data="biolokvar"),
                Button.inline("صورة حسابك", data="phovarlok"),
            ],
            [
                Button.inline("رمز الاسم", data="symnamvar"),
            ],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"symnamvar")))
async def varssett(event):
    await event.edit(
        """نوع الفار: فارات البروفايل
الفار الحالي: فار الرمز

الامر:             `.وضع الرمز`
الشرح :  يقوم هذا الامر بوضع رمز بداية اسم حسابك عند تشغيل امر  .اسم وقتي
الاستخدام : تقوم بالرد على الرمز بالامر   `.وضع الرمز`


ملاحظة : يمكنك استخدام الاوامر في اي دردشة او محادثة
اوامر فارات سورس كرستين  @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="namevar")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"phovarlok")))
async def varssett(event):
    await event.edit(
        """نوع الفار: فارات البروفايل
الفار الحالي: فار الصورة

الامر:             `.وضع الصورة`
الشرح :  يقوم هذا الامر بوضع الصورة الخاصة بحسابك عند تشغيل امر الصورة الوقتية
الاستخدام : تقوم بالرد على رابط الصورة بالامر   `.وضع البايو`

*يمكنك استخدا الزخرفة او اللغة الانكليزية او العربية الخ..


* كيفية جلب رابط الصورة؟
-بالرد على الصورة المراد استخراج منها الرابط ب  `.تلكراف ميديا`


ملاحظة : يمكنك استخدام الاوامر في اي دردشة او محادثة
اوامر فارات سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="namevar")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"biolokvar")))
async def varssett(event):
    await event.edit(
        """نوع الفار: فارات البروفايل
الفار الحالي: فار البايو

الامر:             `.وضع البايو`
الشرح :  يقوم هذا الامر بوضع النبذه او البايو عند تشغيل امر البايو الوقتي
الاستخدام : تقوم بالرد على البايو بالامر   `.وضع البايو`

*يمكنك استخدا الزخرفة او اللغة الانكليزية او العربية الخ..

ملاحظة : يمكنك استخدام الاوامر في اي دردشة او محادثة
اوامر فارات سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="namevar")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"numlokvar")))
async def varssett(event):
    await event.edit(
        """نوع الفار: فارات البروفايل
الفار الحالي: فار الزخرفة

الامر:             `.وضع زخرفة الارقام`
الشرح :  يقوم هذا الامر بتغيير شكل الارقام التي تظهر عند استخدام امر  .اسم وقتي
الاستخدام : تقوم بالرد على الارقام المزخرفة بالامر   `.وضع زخرفة الارقام`

يمكنك استخدام الارقام في الاسفل:

`𝟢 𝟣 𝟤 𝟥 𝟦 𝟧 𝟨 𝟩 𝟪 𝟫 `
`𝟶 𝟷 𝟸 𝟹 𝟺 𝟻 𝟼 𝟽 𝟾  𝟿`
`𝟘 𝟙  𝟚  𝟛  𝟜  𝟝 𝟞 𝟟  𝟠 𝟡`
`𝟎  𝟏  𝟐  𝟑  𝟒  𝟓  𝟔  𝟕  𝟖  𝟗`
`０ １ ２ ３ ４ ５ ６ ７８９`
`𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵`

**ملاحظة: يجب اني تقوم بوضع الزخرفة بالترتيب التالي:**
0123456789
ملاحظة : يمكنك استخدام الاوامر في اي دردشة او محادثة
اوامر فارات سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="namevar")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"nameprvr")))
async def varssett(event):
    await event.edit(
        """نوع الفار: فارات البروفايل
الفار الحالي: فار الاسم

الامر:             `.وضع الاسم`
الشرح :  يقوم هذا الامر بوضع اسم حسابك للعديد من الاوامر مثل الفحص والخ
الاستخدام : تقوم بالرد على اسمك بالامر   `.وضع الاسم`

*يمكنك استخدا الزخرفة او اللغة الانكليزية او العربية الخ..

ملاحظة : يمكنك استخدام الاوامر في اي دردشة او محادثة
اوامر فارات سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="namevar")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"pmvars")))
async def varssett(event):
    await event.edit(
        "من هنا يمكنك عرض شروحات فارات الحماية:",
        buttons=[
            [
                Button.inline("صورة الحماية", data="picpmvar"),
                Button.inline("كليشة الحماية", data="pmvarkish"),
            ],
            [
                Button.inline("كليشة الحظر", data="banklish"),
                Button.inline("عدد التحذيرات", data="warnvars"),
            ],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"banklish")))
async def varssett(event):
    await event.edit(
        """نوع الفار: فارات الحماية
الفار الحالي: فار كليشة الحظر

الامر:             `.وضع كليشة الحظر`
الشرح :  يقوم هذا الامر بتغيير الكليشة (الكلام) التي تظهر عندما تنتهي تحذيرات الشخص ويتم حظره
الاستخدام : تقوم بالرد على الكليشة التي تريد وضعها بالامر   `.وضع كليشة الحظر `

* يمكنك كتابة اي كليشة مثلا: عزيزي المستخدم تم حظرك 


ملاحظة : يمكنك استخدام الاوامر في اي دردشة او محادثة
اوامر فارات سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="pmvars")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"warnvars")))
async def varssett(event):
    await event.edit(
        """نوع الفار: فارات الحماية
الفار الحالي: فار عدد التحذيرات

الامر:             `.وضع عدد التحذيرات`
الشرح :  يقوم هذا الامر بتغيير عدد التحذيرات التي يقوم السورس بتحذير المستخدم بها قبل حظره
الاستخدام : تقوم بالرد على عدد التحذيرات كرقم  بالامر   `.وضع عدد التحذيرات `


ملاحظة : يمكنك استخدام الاوامر في اي دردشة او محادثة
اوامر فارات سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="pmvars")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"pmvarkish")))
async def varssett(event):
    await event.edit(
        """نوع الفار: فارات الحماية
الفار الحالي: فار كليشة الحماية

الامر:             `.وضع كليشة الحماية`
الشرح :  يقوم هذا الامر بتغيير الكليشة (الكلام) التي تظهر عندما يكون امر الحماية شغال ويراسلك احد
الاستخدام : تقوم بالرد على الكليشة التي تريد وضعها بالامر   `.وضع كليشة الحماية `

* يمكنك الحصول على  كليشة جاهزة من هذه القناة @q_k_2 


ملاحظة : يمكنك استخدام الاوامر في اي دردشة او محادثة
اوامر فارات سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="pmvars")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"picpmvar")))
async def varssett(event):
    await event.edit(
        """نوع الفار: فارات الحماية
الفار الحالي: فار صورة الحماية

الامر:             `.وضع صورة الحماية`
الشرح :  يقوم هذا الامر بتغيير او وضع الصورة التي تظهر عندما يكون امر الحماية  شغال ويراسلك احد
الاستخدام : تقوم بالرد على رابط الصورة التي تريد وضعها بالامر   `.وضع صورة الحماية` 

* كيفية جلب رابط الصورة؟
-بالرد على الصورة المراد استخراج منها الرابط ب  `.تلكراف ميديا`

ملاحظة : **يمكنك استخدام الاوامر في اي دردشة او محادثة**
اوامر فارات سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="pmvars")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"alivevar")))
async def varssett(event):
    await event.edit(
        "من هنا يمكنك عرض شروحات فارات الفحص:",
        buttons=[
            [
                Button.inline("صورة الفحص", data="picvars"),
                Button.inline("كليشة الفحص", data="kleshalive"),
            ],
            [Button.inline("رمز الفحص", data="rmzalive")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"picvars")))
async def varssett(event):
    await event.edit(
        """نوع الفار: فارات الفحص
الفار الحالي: فار صورة الفحص

الامر:             `.وضع صورة الفحص`
الشرح :  يقوم هذا الامر بتغيير او وضع الصورة التي تظهر عند ارسال  امر   `.فحص`
الاستخدام : تقوم بالرد على رابط الصورة التي تريد وضعها بالامر   `.وضع صورة الفحص` 

* كيفية جلب رابط الصورة؟
-بالرد على الصورة المراد استخراج منها الرابط ب  `.تلكراف ميديا`

ملاحظة : **يمكنك استخدام الاوامر في اي دردشة او محادثة**
اوامر فارات سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="alivevar")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"kleshalive")))
async def varssett(event):
    await event.edit(
        """ نوع الفار: فارات الفحص
الفار الحالي: فار كليشة الفحص

الامر:             `.وضع كليشة الفحص`
الشرح :  يقوم هذا الامر بتغيير الكليشة (الكلام) التي تظهر عند ارسال  امر  `.فحص`
الاستخدام : تقوم بالرد على الكليشة التي تريد وضعها بالامر   `.وضع كليشة الفحص `

* يمكنك الحصول على  كليشة جاهزة من هذه القناة @q_k_2 


ملاحظة : يمكنك استخدام الاوامر في اي دردشة او محادثة
اوامر فارات سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="alivevar")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"rmzalive")))
async def varssett(event):
    await event.edit(
        """نوع الفار: فارات الفحص
الفار الحالي: فار رمز الفحص


الامر:             `.وضع رمز الفحص`
الشرح :  يقوم هذا الامر بتغيير الرمز  الذي يظهر عند ارسال  امر  `.فحص`
الاستخدام : تقوم بالرد على الرمز التي تريد وضعه بالامر   `.وضع رمز الفحص `


ملاحظة : يمكنك استخدام الاوامر في اي دردشة او محادثة
اوامر فارات سورس كرستين @cr_source""",
        buttons=[
            [Button.inline("رجوع", data="alivevar")],
        ],
    )


@tgbot.on(events.callbackquery.CallbackQuery(data=re.compile(b"CMDBOT")))
async def users(event):
    await event.delete()
    rorza = "**▾∮ قائمه اوامر المطور **\n* تستخدم في ↫ `{BOT_USERNAME} ` فقط! `\n**⍣ⵧⵧⵧⵧⵧⵧSØЦ尺ㄈƐ ㄈ尺ɪらŤɪЛƐⵧⵧⵧⵧ⍣**\n\n*الامر  ( اذاعة  ) \n- لعمل اذاعة لمستخدمي البوت ◛ ↶\n**⋆ قم بالرد ع الرسالة لاذاعتها للمستخدمين ↸**\n\n*الامر ( ايدي ) \n- لمعرفة الملصقات المرسلة ↶\n**⋆ بالرد ع المستخدم لجلب معلوماتة **\n\n*الامر ( حظر + سبب )\n- لحظر مستخدم من البوت \n**⋆ بالرد ع المستخدم مع سبب مثل **\n**حظر @wjj_u قمت بازعاجي**\n\n* الامر ( الغاء حظر ) \n لالغاء حظر المستخدم من البوت √\n**⋆ الامر والمعرف والسبب (اختياري) مثل **\n**الغاء حظر @wjj_u + السبب اختياري**\n\n**⋆ الامر ( المحظورين )\n- لمعرفة المحظورين من البوت  **\n\n**⋆ امر ( المستخدمين ) \n- لمعرفة مستخدمين بوتك  **\n\n**⋆ الاوامر ( التكرار + تفعيل / تعطيل ) \n- تشغيل وايقاف التكرار (في البوت) ↶**\n* عند التشغيل يحظر المزعجين تلقائيًا ⊝\n\n**⋆ امر ( تاك + الكلام ) \n- لعمل تاك للاعضاء يجب ااضافة البوت المساعد في المجموعة اولا و رفعه مشرف\n\n**⋆ امر ( تنظيف ) \n- اضف البوت مشرف بعدها قم بالرد على اي رسالة واكتب تنظيف وسيقوم بحذف الرسائل التي تحتها\n\n⋆ امر ( مسح ) \n- اضف البوت مشرف بعدها قم بالرد على اي رسالة واكتب مسك وسيقوم بحذف الرسالة****\n\n\n**⍣ⵧⵧⵧⵧⵧSØЦ尺ㄈƐ ㄈ尺ɪらŤɪЛƐⵧⵧⵧⵧⵧ⍣**\n𝗖𝗥𝗜𝗦𝗧𝗜𝗡𝗘 𝙐𝙎𝙀𝙍𝘽𝙊𝙏 🧸♥"
    await tgbot.send_message(event.chat_id, rorza)


@sbb_b.bot_cmd(incoming=True, func=lambda e: e.is_private)
async def bot_pms(event):  # sourcery no-metrics
    # sourcery skip: low-code-quality
    chat = await event.get_chat()
    if check_is_black_list(chat.id):
        return
    if chat.id != Config.OWNER_ID:
        msg = await event.forward_to(Config.OWNER_ID)
        try:
            add_user_to_db(msg.id, get_display_name(chat), chat.id, event.id, 0, 0)
        except Exception as e:
            LOGS.error(str(e))
            if BOTLOG:
                await event.client.send_message(
                    BOTLOG_CHATID,
                    f"**خطأ**\nاثناء تخزين الرسالة في قاعدة البيانات:\n`{str(e)}`",
                )
    else:
        if event.text.startswith("/"):
            return
        reply_to = await reply_id(event)
        if reply_to is None:
            return
        users = get_user_id(reply_to)
        if users is None:
            return
        for usr in users:
            user_id = int(usr.chat_id)
            reply_msg = usr.reply_id
            user_name = usr.first_name
            break
        if user_id is not None:
            try:
                if event.media:
                    msg = await event.client.send_file(
                        user_id, event.media, caption=event.text, reply_to=reply_msg
                    )
                else:
                    msg = await event.client.send_message(
                        user_id, event.text, reply_to=reply_msg, link_preview=False
                    )
            except UserIsBlockedError:
                return await event.reply("- البوت محظور من قبل المستخدم")
            except Exception as e:
                return await event.reply(f"**خطا:**\n`{e}`")
            try:
                add_user_to_db(
                    reply_to, user_name, user_id, reply_msg, event.id, msg.id
                )
            except Exception as e:
                LOGS.error(str(e))
                if BOTLOG:
                    await event.client.send_message(
                        BOTLOG_CHATID,
                        f"**خطأ**\nاثناء تخزين الرسالة في قاعدة البيانات:\n`{str(e)}`",
                    )


@sbb_b.bot_cmd(edited=True)
async def bot_pms_edit(event):
    chat = await event.get_chat()
    if check_is_black_list(chat.id):
        return
    if chat.id != Config.OWNER_ID:
        users = get_user_reply(event.id)
        if users is None:
            return
        if reply_msg := next(
            (user.message_id for user in users if user.chat_id == str(chat.id)),
            None,
        ):
            await event.client.send_message(
                Config.OWNER_ID,
                f"⬆️ **الرسالة في الاعلى تم تعديلها من قبل المستخدم** {_format.mentionuser(get_display_name(chat) , chat.id)} الى :",
                reply_to=reply_msg,
            )
            msg = await event.forward_to(Config.OWNER_ID)
            try:
                add_user_to_db(msg.id, get_display_name(chat), chat.id, event.id, 0, 0)
            except Exception as e:
                LOGS.error(str(e))
                if BOTLOG:
                    await event.client.send_message(
                        BOTLOG_CHATID,
                        f"**خطأ**\nاثناء تخزين الرسالة في قاعدة البيانات:\n`(e)`",
                    )

    else:
        reply_to = await reply_id(event)
        if reply_to is not None:
            users = get_user_id(reply_to)
            result_id = 0
            if users is None:
                return
            for usr in users:
                if event.id == usr.logger_id:
                    user_id = int(usr.chat_id)
                    reply_msg = usr.reply_id
                    result_id = usr.result_id
                    break
            if result_id != 0:
                try:
                    await event.client.edit_message(
                        user_id, result_id, event.text, file=event.media
                    )
                except Exception as e:
                    LOGS.error(str(e))


@tgbot.on(events.MessageDeleted)
async def handler(event):
    for msg_id in event.deleted_ids:
        users_1 = get_user_reply(msg_id)
        users_2 = get_user_logging(msg_id)
        if users_2 is not None:
            result_id = 0
            for usr in users_2:
                if msg_id == usr.logger_id:
                    user_id = int(usr.chat_id)
                    result_id = usr.result_id
                    break
            if result_id != 0:
                try:
                    await event.client.delete_messages(user_id, result_id)
                except Exception as e:
                    LOGS.error(str(e))
        if users_1 is not None:
            reply_msg = next(
                (
                    user.message_id
                    for user in users_1
                    if user.chat_id != Config.OWNER_ID
                ),
                None,
            )

            try:
                if reply_msg:
                    users = get_user_id(reply_msg)
                    for usr in users:
                        user_id = int(usr.chat_id)
                        user_name = usr.first_name
                        break
                    if check_is_black_list(user_id):
                        return
                    await event.client.send_message(
                        Config.OWNER_ID,
                        f"⬆️ **الرسالة هذه تم حذفها من قبل المستخدم** {_format.mentionuser(user_name , user_id)}.",
                        reply_to=reply_msg,
                    )
            except Exception as e:
                LOGS.error(str(e))


@sbb_b.bot_cmd(pattern="^ايدي$", from_users=Config.OWNER_ID)
async def bot_start(event):
    reply_to = await reply_id(event)
    if not reply_to:
        return await event.reply(
            "** يجب الرد على رسالة المستخدم التي تريد عرض معلوماته**"
        )
    info_msg = await event.client.send_message(
        event.chat_id,
        "- جار البحث عنه في قاعدة البيانات",
        reply_to=reply_to,
    )
    users = get_user_id(reply_to)
    if users is None:
        return await info_msg.edit("**عذرا لم يتم العثور عليه في قاعدة البيانات**")
    for usr in users:
        user_id = int(usr.chat_id)
        user_name = usr.first_name
        break
    if user_id is None:
        return await info_msg.edit("**عذرا لم يتم العثور عليه في قاعدة البيانات**")
    uinfo = f"👤 المرسل: {_format.mentionuser(user_name , user_id)}\
            \n**الاسم:** {user_name}\
            \n**الايدي:** `{user_id}`"
    await info_msg.edit(uinfo)


async def send_flood_alert(user_) -> None:  # sourcery skip: low-code-quality
    # sourcery no-metrics
    buttons = [
        (
            Button.inline("🚫  حظر", data=f"bot_pm_ban_{user_.id}"),
            Button.inline(
                "➖ مضاد التكرار [ايقاف]",
                data="toggle_bot-antiflood_off",
            ),
        )
    ]
    found = False
    if FloodConfig.ALERT and (user_.id in FloodConfig.ALERT.keys()):
        found = True
        try:
            FloodConfig.ALERT[user_.id]["count"] += 1
        except KeyError:
            found = False
            FloodConfig.ALERT[user_.id]["count"] = 1
        except Exception as e:
            if BOTLOG:
                await sbb_b.tgbot.send_message(
                    BOTLOG_CHATID,
                    f"**خطأ:**\nاثناء تحديث عدد الفولد\n`{e}`",
                )

        flood_count = FloodConfig.ALERT[user_.id]["count"]
    else:
        flood_count = FloodConfig.ALERT[user_.id]["count"] = 1

    flood_msg = (
        r"⚠️ **#تحذير_الفلود**"
        "\n\n"
        f"  الايدي: `{user_.id}`\n"
        f"  الاسم: {get_display_name(user_)}\n"
        f"  👤 User: {_format.mentionuser(get_display_name(user_), user_.id)}"
        f"\n\n**Is spamming your bot !** ->  [ Flood rate ({flood_count}) ]\n"
        "__Quick Action__: Ignored from bot for a while."
    )

    if found:
        if flood_count >= FloodConfig.AUTOBAN:
            if user_.id in Config.SUDO_USERS:
                sudo_spam = (
                    f"**المالك الثانوي** {_format.mentionuser(user_.first_name , user_.id)}:\n  الايدي: {user_.id}\n\n"
                    "يقوم بالتكرار في بوتك يرجى ازالته من قائمة المالكين"
                )
                if BOTLOG:
                    await sbb_b.tgbot.send_message(BOTLOG_CHATID, sudo_spam)
            else:
                await ban_user_from_bot(
                    user_,
                    f"حظر تلقائي بسبب التكرار {FloodConfig.AUTOBAN}",
                )
                FloodConfig.USERS[user_.id].clear()
                FloodConfig.ALERT[user_.id].clear()
                FloodConfig.BANNED_USERS.remove(user_.id)
            return
        fa_id = FloodConfig.ALERT[user_.id].get("fa_id")
        if not fa_id:
            return
        try:
            msg_ = await sbb_b.tgbot.get_messages(BOTLOG_CHATID, fa_id)
            if msg_.text != flood_msg:
                await msg_.edit(flood_msg, buttons=buttons)
        except Exception as fa_id_err:
            LOGS.debug(fa_id_err)
            return
    else:
        if BOTLOG:
            fa_msg = await sbb_b.tgbot.send_message(
                BOTLOG_CHATID,
                flood_msg,
                buttons=buttons,
            )
        try:
            chat = await sbb_b.tgbot.get_entity(BOTLOG_CHATID)
            await sbb_b.tgbot.send_message(
                Config.OWNER_ID,
                f"⚠️  **[تحذير التكرار ](https://t.me/c/{chat.id}/{fa_msg.id})**",
            )
        except UserIsBlockedError:
            if BOTLOG:
                await sbb_b.tgbot.send_message(BOTLOG_CHATID, "**الغاء ححظر بوتك !**")
    if FloodConfig.ALERT[user_.id].get("fa_id") is None and fa_msg:
        FloodConfig.ALERT[user_.id]["fa_id"] = fa_msg.id


@sbb_b.tgbot.on(CallbackQuery(data=re.compile(b"bot_pm_ban_([0-9]+)")))
@check_owner
async def bot_pm_ban_cb(c_q: CallbackQuery):
    user_id = int(c_q.pattern_match.group(1))
    try:
        user = await sbb_b.get_entity(user_id)
    except Exception as e:
        await c_q.answer(f"خطأ:\n{e}")
    else:
        await c_q.answer(f"ايدي المستخدم ا لمحظور -> {user_id} ...", alert=False)
        await ban_user_from_bot(user, "تكرار")
        await c_q.edit(f"✅ **تم بنجاح حظر المستخدم** ايدي المستخدم: {user_id}")


def time_now() -> Union[float, int]:
    return datetime.timestamp(datetime.now())


@pool.run_in_thread
def is_flood(uid: int) -> Optional[bool]:
    """Checks if a user is flooding"""
    FloodConfig.USERS[uid].append(time_now())
    if (
        len(
            list(
                filter(
                    lambda x: time_now() - int(x) < FloodConfig.SECONDS,
                    FloodConfig.USERS[uid],
                )
            )
        )
        > FloodConfig.MESSAGES
    ):
        FloodConfig.USERS[uid] = list(
            filter(
                lambda x: time_now() - int(x) < FloodConfig.SECONDS,
                FloodConfig.USERS[uid],
            )
        )
        return True


@sbb_b.tgbot.on(CallbackQuery(data=re.compile(b"toggle_bot-antiflood_off$")))
@check_owner
async def settings_toggle(c_q: CallbackQuery):
    if gvarstatus("bot_antif") is None:
        return await c_q.answer("البوت مضاد للتكرار تم تعطيله ", alert=False)
    delgvar("bot_antif")
    await c_q.answer("البوت مضاد للتكرار تم تعطيله", alert=False)
    await c_q.edit("مضاد التكرار الان معطل")


@sbb_b.bot_cmd(incoming=True, func=lambda e: e.is_private)
@sbb_b.bot_cmd(edited=True, func=lambda e: e.is_private)
async def antif_on_msg(event):
    if gvarstatus("bot_antif") is None:
        return
    chat = await event.get_chat()
    if chat.id == Config.OWNER_ID:
        return
    user_id = chat.id
    if check_is_black_list(user_id):
        raise StopPropagation
    if await is_flood(user_id):
        await send_flood_alert(chat)
        FloodConfig.BANNED_USERS.add(user_id)
        raise StopPropagation
    if user_id in FloodConfig.BANNED_USERS:
        FloodConfig.BANNED_USERS.remove(user_id)
