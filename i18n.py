"""User-facing texts in Russian, Uzbek (Latin) and English. Admin tools stay in Russian."""
from __future__ import annotations

LANGS = {"ru": "🇷🇺 Русский", "uz": "🇺🇿 O'zbekcha", "en": "🇬🇧 English"}
DEFAULT_LANG = "ru"
_ORDER = ("ru", "uz", "en")

# key: (ru, uz, en)
S: dict[str, tuple[str, str, str]] = {
    # ---- menu buttons ----
    "btn_write": ("✍️ Писать работу", "✍️ Ish yozish", "✍️ Write a paper"),
    "btn_tech": ("🧮 Задачи и код", "🧮 Masala va kod", "🧮 Problems & code"),
    "btn_edit": ("📝 Редактор и перевод", "📝 Muharrir va tarjima", "📝 Editor & translation"),
    "btn_cheat": ("🎓 Шпаргалки и экзамен", "🎓 Shpargalka va imtihon", "🎓 Cheat sheets & exam"),
    "btn_sub": ("💎 Подписка", "💎 Obuna", "💎 Subscription"),
    "btn_new": ("🧹 Новый диалог", "🧹 Yangi suhbat", "🧹 New chat"),
    "btn_support": ("🆘 Поддержка", "🆘 Yordam xizmati", "🆘 Support"),
    "btn_lang": ("🌐 Язык", "🌐 Til", "🌐 Language"),
    "placeholder": ("Напишите вопрос или пришлите файл", "Savol yozing yoki fayl yuboring", "Type a question or send a file"),
    # ---- start ----
    "choose_lang": ("🌐 Выберите язык / Tilni tanlang / Choose your language", "", ""),
    "lang_set": ("✅ Язык: русский", "✅ Til: o'zbekcha", "✅ Language: English"),
    "welcome": (
        "👋 <b>Привет! Я OmniStudent</b>, академический помощник для студентов.\n\n"
        "✍️ пишу курсовые, рефераты, эссе и планы работ\n"
        "🧮 решаю задачи и пишу код с пошаговым объяснением\n"
        "📝 редактирую, делаю рерайт и перевожу научные тексты\n"
        "🎓 делаю шпаргалки и устраиваю «Вредного преподавателя» перед защитой\n\n"
        "Выберите режим в меню или просто напишите вопрос. Файлы .txt, .pdf и .docx тоже читаю.\n"
        "Нужна помощь по боту? Кнопка «🆘 Поддержка».",
        "👋 <b>Salom! Men OmniStudent</b>man, talabalar uchun akademik yordamchi.\n\n"
        "✍️ kurs ishi, referat, esse va ish rejalarini yozaman\n"
        "🧮 masalalarni yechaman va kodni bosqichma-bosqich tushuntirib yozaman\n"
        "📝 ilmiy matnlarni tahrirlayman, qayta yozaman va tarjima qilaman\n"
        "🎓 shpargalka tayyorlayman va himoya oldidan «Qattiq o'qituvchi» bo'laman\n\n"
        "Menyudan rejimni tanlang yoki shunchaki savol yozing. .txt, .pdf va .docx fayllarni ham o'qiyman.\n"
        "Bot bo'yicha yordam kerakmi? «🆘 Yordam xizmati» tugmasi.",
        "👋 <b>Hi! I'm OmniStudent</b>, an academic assistant for students.\n\n"
        "✍️ I write term papers, reports, essays and outlines\n"
        "🧮 I solve problems and write code with step-by-step explanations\n"
        "📝 I edit, rewrite and translate academic texts\n"
        "🎓 I make cheat sheets and play the «Tough Professor» before your defense\n\n"
        "Pick a mode in the menu or just ask a question. I can read .txt, .pdf and .docx files too.\n"
        "Need help with the bot? Tap «🆘 Support».",
    ),
    "help": (
        "<b>Команды</b>\n/start главное меню\n/new новый диалог (забыть контекст)\n/subscribe подписка за Telegram Stars\n"
        "/stars как купить Stars\n/support написать в поддержку\n/lang сменить язык\n/paysupport вопросы по оплате\n/id ваш Telegram ID\n\n"
        "Совет: чем точнее задача (тема, объём, стандарт оформления, дедлайн), тем лучше результат.",
        "<b>Buyruqlar</b>\n/start asosiy menyu\n/new yangi suhbat (kontekstni unutish)\n/subscribe Telegram Stars orqali obuna\n"
        "/stars Stars qanday sotib olinadi\n/support yordam xizmatiga yozish\n/lang tilni almashtirish\n/paysupport to'lov bo'yicha savollar\n/id sizning Telegram ID\n\n"
        "Maslahat: topshiriq qanchalik aniq bo'lsa (mavzu, hajm, rasmiylashtirish standarti, muddat), natija shunchalik yaxshi.",
        "<b>Commands</b>\n/start main menu\n/new new chat (forget the context)\n/subscribe subscription via Telegram Stars\n"
        "/stars how to buy Stars\n/support contact support\n/lang change language\n/paysupport payment questions\n/id your Telegram ID\n\n"
        "Tip: the more precise the task (topic, length, formatting standard, deadline), the better the result.",
    ),
    "your_id": ("Ваш Telegram ID: <code>{id}</code>", "Sizning Telegram ID: <code>{id}</code>", "Your Telegram ID: <code>{id}</code>"),
    "new_done": (
        "🧹 Диалог очищен. Начнём с чистого листа: выберите режим или напишите вопрос.",
        "🧹 Suhbat tozalandi. Yangi sahifadan boshlaymiz: rejimni tanlang yoki savol yozing.",
        "🧹 Chat cleared. A fresh start: pick a mode or ask a question."),
    # ---- modes ----
    "cheat_ask": ("🎓 Что нужно?", "🎓 Nima kerak?", "🎓 What do you need?"),
    "cheat_btn": ("📋 Шпаргалка из материала", "📋 Materialdan shpargalka", "📋 Cheat sheet from material"),
    "exam_btn": ("😈 Вредный преподаватель", "😈 Qattiq o'qituvchi", "😈 Tough Professor"),
    "intro_writer": (
        "✍️ <b>Академический писатель</b>\n\nПомогу с курсовой, рефератом, эссе или дипломной: план, оглавление, введение, "
        "главы, выводы, список литературы.\n\nНапишите тему и, если знаете, объём и стандарт оформления вуза. "
        "Например: <i>«Курсовая по маркетингу, тема: digital-стратегии ресторанов, 30 страниц, ГОСТ»</i>.",
        "✍️ <b>Akademik yozuvchi</b>\n\nKurs ishi, referat, esse yoki diplom ishida yordam beraman: reja, mundarija, kirish, "
        "boblar, xulosa, adabiyotlar ro'yxati.\n\nMavzuni yozing, bilsangiz hajm va universitet standartini ham. "
        "Masalan: <i>«Marketing fanidan kurs ishi, mavzu: restoranlarning digital-strategiyalari, 30 bet»</i>.",
        "✍️ <b>Academic writer</b>\n\nI'll help with a term paper, report, essay or thesis: outline, table of contents, introduction, "
        "chapters, conclusions, references.\n\nSend the topic and, if you know them, the length and your university's formatting standard. "
        "For example: <i>\"Marketing term paper, topic: digital strategies of restaurants, 30 pages\"</i>."),
    "intro_tech": (
        "🧮 <b>Технический эксперт</b>\n\nРешаю задачи по математике, физике, экономике и программированию "
        "с пошаговым объяснением. Код пишу рабочим, с комментариями и инструкцией запуска.\n\nПришлите условие задачи или текст задания.",
        "🧮 <b>Texnik mutaxassis</b>\n\nMatematika, fizika, iqtisodiyot va dasturlashdan masalalarni bosqichma-bosqich tushuntirib yechaman. "
        "Kodni ishlaydigan, izohlar va ishga tushirish yo'riqnomasi bilan yozaman.\n\nMasala shartini yoki topshiriq matnini yuboring.",
        "🧮 <b>Technical expert</b>\n\nI solve math, physics, economics and programming problems with step-by-step explanations. "
        "My code is working, commented, and comes with run instructions.\n\nSend the problem statement or the assignment text."),
    "intro_editor": (
        "📝 <b>Редактор и переводчик</b>\n\nПроверю орфографию и логику, сделаю академический рерайт без потери смысла, "
        "переведу научный текст с сохранением терминологии.\n\nПришлите текст или файл (.txt, .pdf, .docx) и напишите, что сделать.",
        "📝 <b>Muharrir va tarjimon</b>\n\nImlo va mantiqni tekshiraman, ma'noni yo'qotmasdan akademik qayta yozaman, "
        "ilmiy matnni terminologiyani saqlab tarjima qilaman.\n\nMatn yoki fayl (.txt, .pdf, .docx) yuboring va nima qilish kerakligini yozing.",
        "📝 <b>Editor & translator</b>\n\nI'll check spelling and logic, do an academic rewrite without losing meaning, "
        "and translate scientific text keeping the terminology.\n\nSend a text or a file (.txt, .pdf, .docx) and say what to do."),
    "intro_cheat": (
        "📋 <b>Шпаргалка</b>\n\nПришлите конспект, лекцию или файл (.txt, .pdf, .docx), и я сделаю краткую выжимку: "
        "определения, формулы, ключевые мысли.",
        "📋 <b>Shpargalka</b>\n\nKonspekt, ma'ruza yoki fayl (.txt, .pdf, .docx) yuboring, men qisqa xulosa qilaman: "
        "ta'riflar, formulalar, asosiy fikrlar.",
        "📋 <b>Cheat sheet</b>\n\nSend your notes, a lecture or a file (.txt, .pdf, .docx) and I'll make a short digest: "
        "definitions, formulas, key ideas."),
    "intro_exam": (
        "😈 <b>Вредный преподаватель</b>\n\nПришлите тему или текст курсовой, и я буду задавать каверзные вопросы по одному, "
        "как на защите. Отвечайте, а я скажу, что слабо.\n\nЧтобы начать, напишите: <i>«Начинай»</i> и дайте тему работы.",
        "😈 <b>Qattiq o'qituvchi</b>\n\nMavzu yoki kurs ishi matnini yuboring, men himoyadagidek bitta-bitta qiyin savollar beraman. "
        "Javob bering, men nima zaif ekanini aytaman.\n\nBoshlash uchun yozing: <i>«Boshla»</i> va ish mavzusini bering.",
        "😈 <b>Tough Professor</b>\n\nSend the topic or the text of your paper and I'll ask tricky questions one at a time, "
        "like at a defense. Answer, and I'll tell you what is weak.\n\nTo begin, write <i>\"Start\"</i> and give the topic."),
    "file_task_cheat": (
        "Сделай из этого материала краткую шпаргалку: определения, формулы, ключевые мысли.",
        "Bu materialdan qisqa shpargalka tayyorla: ta'riflar, formulalar, asosiy fikrlar. O'zbek tilida javob ber.",
        "Make a short cheat sheet from this material: definitions, formulas, key ideas. Answer in English."),
    "file_task_editor": (
        "Проверь текст: исправь ошибки, улучши стиль и логику. Коротко перечисли, что изменил.",
        "Matnni tekshir: xatolarni tuzat, uslub va mantiqni yaxshila. Nimani o'zgartirganingni qisqa yoz. O'zbek tilida javob ber.",
        "Check the text: fix errors, improve style and logic. Briefly list what you changed. Answer in English."),
    "file_task_exam": (
        "Прочитай работу и начни экзамен: задай первый каверзный вопрос по ней.",
        "Ishni o'qib chiq va imtihonni boshla: u bo'yicha birinchi qiyin savolni ber. O'zbek tilida javob ber.",
        "Read the paper and start the exam: ask the first tricky question about it. Answer in English."),
    "file_task_default": (
        "Кратко изложи суть этого материала и предложи, что с ним можно сделать.",
        "Bu materialning mohiyatini qisqa bayon qil va u bilan nima qilish mumkinligini taklif qil. O'zbek tilida javob ber.",
        "Summarize this material briefly and suggest what can be done with it. Answer in English."),
    "file_note": ("\n(Файл длинный, прочитаны первые 30 000 знаков.)", "\n(Fayl uzun, dastlabki 30 000 belgi o'qildi.)",
                  "\n(The file is long, the first 30,000 characters were read.)"),
    "file_big": ("Файл слишком большой: максимум 10 МБ.", "Fayl juda katta: eng ko'pi bilan 10 MB.", "The file is too large: 10 MB maximum."),
    "file_bad": ("Я читаю файлы .txt, .md, .pdf и .docx. Пришлите один из этих форматов.",
                 "Men .txt, .md, .pdf va .docx fayllarni o'qiyman. Shu formatlardan birini yuboring.",
                 "I read .txt, .md, .pdf and .docx files. Please send one of these formats."),
    "too_long": (
        "Сообщение слишком длинное (максимум {n} знаков). Пришлите текст файлом (.txt, .pdf, .docx) или разбейте на части.",
        "Xabar juda uzun (eng ko'pi bilan {n} belgi). Matnni fayl (.txt, .pdf, .docx) sifatida yuboring yoki qismlarga bo'ling.",
        "The message is too long ({n} characters max). Send the text as a file (.txt, .pdf, .docx) or split it into parts."),
    "other": ("Я работаю с текстом и файлами .txt, .pdf, .docx. Напишите вопрос или пришлите файл.",
              "Men matn va .txt, .pdf, .docx fayllar bilan ishlayman. Savol yozing yoki fayl yuboring.",
              "I work with text and .txt, .pdf, .docx files. Write a question or send a file."),
    # ---- subscription ----
    "sub_active": (
        "💎 <b>Подписка активна</b> до {until}.\nРазвёрнутые ответы и до {paid} запросов в день.",
        "💎 <b>Obuna faol</b>, {until} gacha.\nBatafsil javoblar va kuniga {paid} tagacha so'rov.",
        "💎 <b>Subscription active</b> until {until}.\nFull-length answers and up to {paid} requests per day."),
    "sub_free": (
        "🆓 <b>Бесплатный тариф</b>: осталось запросов сегодня: {left} из {free}. Ответы компактные.\n\n"
        "💎 <b>Подписка на {days} дней за {price} ⭐</b>:\n• до {paid} запросов в день\n"
        "• большие главы курсовых и развёрнутые тексты\n• длинные ответы без обрезки",
        "🆓 <b>Bepul tarif</b>: bugun {free} tadan {left} ta so'rov qoldi. Javoblar ixcham.\n\n"
        "💎 <b>{days} kunlik obuna — {price} ⭐</b>:\n• kuniga {paid} tagacha so'rov\n"
        "• kurs ishlarining katta boblari va batafsil matnlar\n• uzun javoblar qisqartirilmaydi",
        "🆓 <b>Free plan</b>: {left} of {free} requests left today. Answers are compact.\n\n"
        "💎 <b>{days}-day subscription for {price} ⭐</b>:\n• up to {paid} requests per day\n"
        "• large chapters and full-length texts\n• long answers without cutting"),
    "pay_btn": ("⭐ Оплатить {price} Stars", "⭐ {price} Stars to'lash", "⭐ Pay {price} Stars"),
    "pay_btn_sub": ("⭐ Оформить подписку, {price} Stars", "⭐ Obuna olish, {price} Stars", "⭐ Subscribe, {price} Stars"),
    "invoice_title": ("OmniStudent: подписка на {days} дней", "OmniStudent: {days} kunlik obuna", "OmniStudent: {days}-day subscription"),
    "invoice_desc": (
        "Развёрнутые ответы, большие главы работ и до {paid} запросов в день.",
        "Batafsil javoblar, ishlarning katta boblari va kuniga {paid} tagacha so'rov.",
        "Full-length answers, large chapters and up to {paid} requests per day."),
    "invoice_label": ("Подписка {days} дней", "{days} kunlik obuna", "{days}-day subscription"),
    "bad_invoice": ("Счёт устарел. Откройте меню подписки и создайте новый.",
                    "Hisob eskirgan. Obuna menyusini oching va yangisini yarating.",
                    "This invoice has expired. Open the subscription menu and create a new one."),
    "paid_ok": (
        "✅ <b>Спасибо! Подписка активна до {until}.</b>\nТеперь доступны развёрнутые ответы и большие главы.",
        "✅ <b>Rahmat! Obuna {until} gacha faol.</b>\nEndi batafsil javoblar va katta boblar mavjud.",
        "✅ <b>Thank you! Your subscription is active until {until}.</b>\nFull-length answers and large chapters are now available."),
    "granted": ("💎 Вам включена подписка до {until}.", "💎 Sizga {until} gacha obuna yoqildi.", "💎 A subscription has been enabled for you until {until}."),
    "paysupport": (
        "💬 <b>Вопросы по оплате.</b> Если оплата прошла, а подписка не включилась, или вы хотите вернуть Stars, "
        "нажмите «🆘 Поддержка» и сообщите ID платежа из чата с чеком.",
        "💬 <b>To'lov bo'yicha savollar.</b> To'lov o'tgan, lekin obuna yoqilmagan bo'lsa yoki Stars qaytarmoqchi bo'lsangiz, "
        "«🆘 Yordam xizmati» tugmasini bosing va chekdagi to'lov ID sini yozing.",
        "💬 <b>Payment questions.</b> If a payment went through but the subscription did not activate, or you want a Stars refund, "
        "tap «🆘 Support» and send the payment ID from the receipt chat."),
    # ---- limits and errors ----
    "limit_paid": ("Вы исчерпали дневной лимит ({n} запросов). Он обновится завтра.",
                   "Kunlik limit tugadi ({n} ta so'rov). U ertaga yangilanadi.",
                   "You have used your daily limit ({n} requests). It resets tomorrow."),
    "limit_free": (
        "На сегодня бесплатные запросы закончились ({n}). С подпиской за {price} ⭐ доступно до {paid} запросов в день "
        "и большие главы работ. Лимит бесплатного тарифа обновится завтра.",
        "Bugungi bepul so'rovlar tugadi ({n}). {price} ⭐ evaziga obuna bilan kuniga {paid} tagacha so'rov va ishlarning katta boblari "
        "mavjud. Bepul tarif limiti ertaga yangilanadi.",
        "Today's free requests are used up ({n}). A {price} ⭐ subscription gives up to {paid} requests a day and large chapters. "
        "The free limit resets tomorrow."),
    "last_free": ("Это был последний бесплатный запрос на сегодня.", "Bu bugungi oxirgi bepul so'rov edi.", "That was the last free request for today."),
    "busy": ("Я ещё отвечаю на предыдущий вопрос. Дождитесь ответа, пожалуйста.",
             "Men hali oldingi savolga javob bermoqdaman. Iltimos, javobni kuting.",
             "I'm still answering your previous question. Please wait for the answer."),
    "generic_error": ("⚠️ Что-то пошло не так. Попробуйте ещё раз через минуту.", "⚠️ Nimadir xato ketdi. Bir daqiqadan so'ng qayta urinib ko'ring.",
                      "⚠️ Something went wrong. Please try again in a minute."),
    "truncated": (
        "\n\n…ответ обрезан лимитом тарифа. Напишите «продолжи», чтобы получить следующую часть{upsell}.",
        "\n\n…javob tarif limiti bilan qisqartirildi. Keyingi qismini olish uchun «davom et» deb yozing{upsell}.",
        "\n\n…the answer was cut by the plan limit. Write «continue» to get the next part{upsell}."),
    "truncated_upsell": (", а полные объёмные ответы доступны по подписке: /subscribe", ", to'liq katta javoblar esa obuna orqali: /subscribe",
                         ", and full long answers are available with a subscription: /subscribe"),
    "err_not_ready": ("Ассистент пока не подключён. Попробуйте позже.", "Yordamchi hali ulanmagan. Keyinroq urinib ko'ring.",
                      "The assistant is not connected yet. Please try later."),
    "err_access": ("Ассистент временно недоступен: проблема с доступом к ИИ-сервису.", "Yordamchi vaqtincha mavjud emas: sun'iy intellekt xizmatiga kirishda muammo.",
                   "The assistant is temporarily unavailable: a problem with the AI service access."),
    "err_balance": ("Ассистент временно недоступен: на стороне сервиса закончился баланс. Мы уже занимаемся этим.",
                    "Yordamchi vaqtincha mavjud emas: xizmat balansi tugagan. Biz buni hal qilmoqdamiz.",
                    "The assistant is temporarily unavailable: the service balance ran out. We are working on it."),
    "err_bad_request": ("Не удалось обработать запрос. Попробуйте сократить сообщение.", "So'rovni qayta ishlab bo'lmadi. Xabarni qisqartirib ko'ring.",
                        "The request could not be processed. Try shortening the message."),
    "err_overloaded": ("ИИ-сервис сейчас перегружен. Попробуйте через минуту.", "Sun'iy intellekt xizmati hozir band. Bir daqiqadan so'ng urinib ko'ring.",
                       "The AI service is overloaded right now. Please try again in a minute."),
    "err_connection": ("Нет связи с ИИ-сервисом. Попробуйте ещё раз.", "Sun'iy intellekt xizmati bilan aloqa yo'q. Qayta urinib ko'ring.",
                       "No connection to the AI service. Please try again."),
    "err_empty": ("Модель вернула пустой ответ. Попробуйте переформулировать вопрос.", "Model bo'sh javob qaytardi. Savolni boshqacha yozib ko'ring.",
                  "The model returned an empty answer. Try rephrasing your question."),
    "banned": ("⛔ Доступ к боту ограничен.", "⛔ Botdan foydalanish cheklangan.", "⛔ Your access to the bot is restricted."),
    # ---- support ----
    "support_intro": (
        "🆘 <b>Поддержка</b>\n\nОпишите проблему или вопрос одним сообщением (можно приложить фото или файл). "
        "Мы ответим прямо здесь, в боте.\n\nОтмена: /cancel",
        "🆘 <b>Yordam xizmati</b>\n\nMuammo yoki savolingizni bitta xabarda yozing (rasm yoki fayl ham biriktirish mumkin). "
        "Javobni shu yerning o'zida, botda beramiz.\n\nBekor qilish: /cancel",
        "🆘 <b>Support</b>\n\nDescribe your problem or question in one message (you can attach a photo or a file). "
        "We will answer right here in the bot.\n\nCancel: /cancel"),
    "support_sent": ("✅ Обращение <b>#{id}</b> принято. Мы ответим здесь, как только сможем.",
                     "✅ <b>#{id}</b>-murojaat qabul qilindi. Imkon qadar tezroq shu yerda javob beramiz.",
                     "✅ Request <b>#{id}</b> received. We will reply here as soon as we can."),
    "support_cancel": ("Отменено.", "Bekor qilindi.", "Cancelled."),
    "support_empty": ("Пришлите текст, фото или файл.", "Matn, rasm yoki fayl yuboring.", "Please send text, a photo or a file."),
    "support_reply": ("💬 <b>Ответ поддержки по обращению #{id}</b>\n\n{text}\n\nЕсли вопрос не решён, нажмите «🆘 Поддержка».",
                      "💬 <b>#{id}-murojaat bo'yicha yordam xizmati javobi</b>\n\n{text}\n\nMuammo hal bo'lmagan bo'lsa, «🆘 Yordam xizmati» tugmasini bosing.",
                      "💬 <b>Support reply to request #{id}</b>\n\n{text}\n\nIf this is not solved, tap «🆘 Support»."),
    "support_closed": ("✅ Обращение #{id} закрыто.", "✅ #{id}-murojaat yopildi.", "✅ Request #{id} is closed."),
    "support_limit": ("Вы уже отправили несколько обращений подряд. Подождите ответа, пожалуйста.",
                      "Siz ketma-ket bir nechta murojaat yubordingiz. Iltimos, javobni kuting.",
                      "You have sent several requests in a row. Please wait for a reply."),
    "cancel_btn": ("✖️ Отмена", "✖️ Bekor qilish", "✖️ Cancel"),
}

from i18n_tools import TOOLS  # noqa: E402

S.update(TOOLS)


def t(lang: str | None, key: str, **kw) -> str:
    row = S[key]
    i = _ORDER.index(lang) if lang in _ORDER else 0
    text = row[i] or row[0]
    return text.format(**kw) if kw else text


def labels(key: str) -> set[str]:
    """Every translation of a button label, for handlers that must match whatever language the user has."""
    return {x for x in S[key] if x}
