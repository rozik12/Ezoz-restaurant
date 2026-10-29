"""Texts of the order wizards (written works, slides) and "My works" in ru, uz, en."""
ORD: dict[str, tuple[str, str, str]] = {
    "btn_works": ("📂 Мои работы", "📂 Mening ishlarim", "📂 My works"),
    "btn_skip": ("⏭ Пропустить", "⏭ O'tkazib yuborish", "⏭ Skip"),
    "btn_other_number": ("✏️ Другое число", "✏️ Boshqa son", "✏️ Other number"),
    "btn_custom_volume": ("✏️ Свой объём", "✏️ O'z hajmim", "✏️ Own length"),
    "btn_edit_order": ("✏️ Изменить", "✏️ O'zgartirish", "✏️ Change"),
    "btn_cancel_order": ("✖️ Отмена", "✖️ Bekor qilish", "✖️ Cancel"),
    "btn_go": ("✅ Начать ({price} ⭐)", "✅ Boshlash ({price} ⭐)", "✅ Start ({price} ⭐)"),
    "order_old": ("Заказ устарел (бот перезапускался). Начните заново.", "Buyurtma eskirgan (bot qayta ishga tushgan). Qaytadan boshlang.",
                  "This order is out of date (the bot restarted). Please start again."),
    "order_none": ("—", "—", "—"),
    # ---- kinds ----
    "kind_course": ("Курсовая", "Kurs ishi", "Term paper"),
    "kind_referat": ("Реферат", "Referat", "Report"),
    "kind_essay": ("Эссе", "Esse", "Essay"),
    "kind_report": ("Доклад", "Ma'ruza", "Speech / report"),
    "kind_practice": ("Отчёт по практике", "Amaliyot hisoboti", "Internship report"),
    "kind_thesis": ("Глава диплома", "Bitiruv ishi bobi", "Thesis chapter"),
    "kind_free": ("Свободный запрос", "Erkin so'rov", "Free request"),
    "std_gost": ("ГОСТ", "GOST", "GOST"),
    "std_apa": ("APA", "APA", "APA"),
    "std_none": ("Без стандарта", "Standartsiz", "No standard"),
    # ---- paper wizard ----
    "paper_start": (
        "✍️ <b>Что пишем?</b>\n\nВыберите тип работы. Я спрошу тему, язык, объём и требования, а потом соберу готовый файл .docx "
        "в вузовском оформлении: поля 30/10/20/20 мм, Times New Roman 14, интервал 1,5, нумерация страниц, титульный лист и содержание.\n\n"
        "«💬 Свободный запрос» это обычный чат с писателем: задайте любой вопрос по тексту.",
        "✍️ <b>Nima yozamiz?</b>\n\nIsh turini tanlang. Men mavzu, til, hajm va talablarni so'rayman, keyin universitet andozasidagi tayyor .docx faylni yig'aman: "
        "maydonlar 30/10/20/20 mm, Times New Roman 14, 1,5 interval, sahifa raqamlari, titul varag'i va mundarija.\n\n"
        "«💬 Erkin so'rov» yozuvchi bilan oddiy suhbat: matn bo'yicha istalgan savolni bering.",
        "✍️ <b>What shall we write?</b>\n\nChoose the type of work. I'll ask for the topic, language, length and requirements, then build a ready .docx in university layout: "
        "margins 30/10/20/20 mm, Times New Roman 14, 1.5 spacing, page numbers, a title page and contents.\n\n"
        "«💬 Free request» is an ordinary chat with the writer: ask anything about a text."),
    "paper_topic": (
        "📌 <b>Тема работы.</b> Напишите её одним сообщением. Можно добавить предмет и специальность, например: "
        "<i>«Цифровой маркетинг в ресторанном бизнесе, дисциплина «Маркетинг»»</i>.\nОтмена: /cancel",
        "📌 <b>Ish mavzusi.</b> Uni bitta xabarda yozing. Fan va mutaxassislikni ham qo'shish mumkin, masalan: "
        "<i>«Restoran biznesida raqamli marketing, «Marketing» fani»</i>.\nBekor qilish: /cancel",
        "📌 <b>Topic.</b> Write it in one message. You may add the subject and specialty, e.g. "
        "<i>\"Digital marketing in the restaurant business, subject: Marketing\"</i>.\nCancel: /cancel"),
    "paper_lang": ("🌐 На каком языке писать работу?", "🌐 Ishni qaysi tilda yozamiz?", "🌐 In which language should the work be written?"),
    "paper_volume": (
        "📏 <b>Какой нужен объём?</b>\n\nВыберите вариант или напишите свой: слова или страницы, число или диапазон. "
        "Примеры: <code>7000-9000 слов</code>, <code>25 страниц</code>, <code>3000</code>. Одна страница ≈ {wpp} слов (Times New Roman 14, интервал 1,5). "
        "Если в методичке указан диапазон, берите именно его.",
        "📏 <b>Qancha hajm kerak?</b>\n\nVariantni tanlang yoki o'zingiznikini yozing: so'z yoki sahifa, son yoki oraliq. "
        "Misollar: <code>7000-9000 so'z</code>, <code>25 bet</code>, <code>3000</code>. Bir sahifa ≈ {wpp} so'z (Times New Roman 14, 1,5 interval). "
        "Uslubiy qo'llanmada oraliq ko'rsatilgan bo'lsa, aynan uni oling.",
        "📏 <b>How long should it be?</b>\n\nChoose an option or write your own: words or pages, a number or a range. "
        "Examples: <code>7000-9000 words</code>, <code>25 pages</code>, <code>3000</code>. One page ≈ {wpp} words (Times New Roman 14, 1.5 spacing). "
        "If your guidelines give a range, use exactly that."),
    "paper_volume_btn": ("{a}–{b} слов (≈ {p} стр.)", "{a}–{b} so'z (≈ {p} bet)", "{a}–{b} words (≈ {p} pp.)"),
    "paper_volume_bad": (
        "Не понял объём. Напишите, например: <code>5000-6000 слов</code> или <code>20 страниц</code> (от 200 до 40 000 слов).",
        "Hajmni tushunmadim. Masalan: <code>5000-6000 so'z</code> yoki <code>20 bet</code> (200 dan 40 000 so'zgacha).",
        "I did not understand the length. Write e.g. <code>5000-6000 words</code> or <code>20 pages</code> (200 to 40,000 words)."),
    "paper_std": ("📐 <b>Оформление и стиль.</b> Выберите стандарт:", "📐 <b>Rasmiylashtirish va uslub.</b> Standartni tanlang:",
                  "📐 <b>Formatting and style.</b> Choose a standard:"),
    "paper_extra": (
        "📎 <b>Особые требования.</b> Есть методичка, свой план или пожелания (структура, обязательные вопросы, что исследовать)? "
        "Напишите текстом или пришлите файл (.txt, .pdf, .docx). Если нет, нажмите «Пропустить».",
        "📎 <b>Maxsus talablar.</b> Uslubiy qo'llanma, o'z rejangiz yoki istaklaringiz (tuzilma, majburiy savollar, nimani o'rganish) bormi? "
        "Matn yozing yoki fayl (.txt, .pdf, .docx) yuboring. Yo'q bo'lsa, «O'tkazib yuborish» ni bosing.",
        "📎 <b>Special requirements.</b> Do you have guidelines, your own outline or wishes (structure, mandatory questions, what to research)? "
        "Write them or send a file (.txt, .pdf, .docx). If not, tap «Skip»."),
    "paper_confirm": (
        "📝 <b>Проверьте заказ</b>\n\n▫️ Тип: {kind}\n▫️ Тема: {topic}\n▫️ Язык: {wlang}\n▫️ Объём: {wmin}–{wmax} слов (≈ {pmin}–{pmax} стр.)\n"
        "▫️ Оформление: {std}\n▫️ Требования: {extra}\n\n💰 Стоимость: <b>{price} ⭐</b> · баланс: {balance} ⭐\n"
        "Готовую работу пришлю файлом .docx, это займёт несколько минут. Если не получится, звёзды вернутся.",
        "📝 <b>Buyurtmani tekshiring</b>\n\n▫️ Turi: {kind}\n▫️ Mavzu: {topic}\n▫️ Til: {wlang}\n▫️ Hajm: {wmin}–{wmax} so'z (≈ {pmin}–{pmax} bet)\n"
        "▫️ Rasmiylashtirish: {std}\n▫️ Talablar: {extra}\n\n💰 Narxi: <b>{price} ⭐</b> · balans: {balance} ⭐\n"
        "Tayyor ishni .docx fayl sifatida yuboraman, bir necha daqiqa ketadi. Bajarilmasa, yulduzlar qaytariladi.",
        "📝 <b>Check your order</b>\n\n▫️ Type: {kind}\n▫️ Topic: {topic}\n▫️ Language: {wlang}\n▫️ Length: {wmin}–{wmax} words (≈ {pmin}–{pmax} pp.)\n"
        "▫️ Formatting: {std}\n▫️ Requirements: {extra}\n\n💰 Price: <b>{price} ⭐</b> · balance: {balance} ⭐\n"
        "I'll send the finished work as a .docx file, it takes a few minutes. If it fails, the Stars are returned."),
    "paper_p_plan": ("⏳ Составляю план работы…", "⏳ Ish rejasini tuzmoqdaman…", "⏳ Drafting the outline…"),
    "paper_p_write": ("⏳ Пишу работу: готово {done} из {total} разделов…", "⏳ Ish yozilmoqda: {done} / {total} bo'lim tayyor…",
                      "⏳ Writing the work: {done} of {total} sections done…"),
    "paper_p_expand": ("⏳ Довожу объём до нужного…", "⏳ Hajmni kerakli darajaga yetkazmoqdaman…", "⏳ Bringing it up to the required length…"),
    "paper_p_biblio": ("⏳ Собираю список литературы и оформляю файл…", "⏳ Adabiyotlar ro'yxatini yig'ib, faylni rasmiylashtirmoqdaman…",
                       "⏳ Compiling references and formatting the file…"),
    "paper_done": (
        "✅ <b>Готово!</b> {words} слов (≈ {pages} стр.), разделов: {n}.\n{range_note}\n\n"
        "⚠️ Проверьте факты, цифры и список литературы: бот мог ошибиться. Вместо [данных в скобках] подставьте свои, титульный лист заполните сами.",
        "✅ <b>Tayyor!</b> {words} so'z (≈ {pages} bet), bo'limlar: {n}.\n{range_note}\n\n"
        "⚠️ Faktlar, raqamlar va adabiyotlar ro'yxatini tekshiring: bot xato qilgan bo'lishi mumkin. [Qavs ichidagi ma'lumotlar] o'rniga o'zingiznikini qo'ying, titul varag'ini o'zingiz to'ldiring.",
        "✅ <b>Done!</b> {words} words (≈ {pages} pp.), sections: {n}.\n{range_note}\n\n"
        "⚠️ Check the facts, figures and references: the bot can be wrong. Replace the [bracketed data] with your own and fill in the title page yourself."),
    "range_ok": ("Объём в нужном диапазоне {wmin}–{wmax} слов.", "Hajm kerakli oraliqda: {wmin}–{wmax} so'z.", "The length is within the required {wmin}–{wmax} words."),
    "range_miss": ("Нужно было {wmin}–{wmax} слов, получилось {words}. Продолжите в «💬 Свободный запрос» («дополни раздел …») или закажите заново.",
                   "Kerak edi {wmin}–{wmax} so'z, chiqdi {words}. «💬 Erkin so'rov» da davom eting («… bo'limini to'ldir») yoki qaytadan buyurtma bering.",
                   "You needed {wmin}–{wmax} words, got {words}. Continue in «💬 Free request» (\"extend section …\") or order again."),
    "paper_fail": ("Не удалось написать работу целиком.", "Ishni to'liq yozib bo'lmadi.", "The work could not be written in full."),
    # ---- slides wizard ----
    "slides_intro": (
        "📊 <b>Презентация</b>\n\nНапишите тему, можно сразу с числом слайдов («Цифровой маркетинг, 12 слайдов»). "
        "Или пришлите файл (.txt, .pdf, .docx), и я сделаю презентацию по нему. Получите готовый .pptx для PowerPoint.\n\nОтмена: /cancel",
        "📊 <b>Taqdimot</b>\n\nMavzuni yozing, slaydlar sonini ham ko'rsatish mumkin («Raqamli marketing, 12 slayd»). "
        "Yoki fayl (.txt, .pdf, .docx) yuboring, men uning asosida taqdimot qilaman. PowerPoint uchun tayyor .pptx olasiz.\n\nBekor qilish: /cancel",
        "📊 <b>Presentation</b>\n\nSend the topic, optionally with a slide count (\"Digital marketing, 12 slides\"). "
        "Or send a file (.txt, .pdf, .docx) and I'll build the deck from it. You get a ready .pptx for PowerPoint.\n\nCancel: /cancel"),
    "slides_count": (
        "🔢 <b>Сколько слайдов нужно?</b>\nВыберите или напишите число от 3 до 30. Ориентир: один слайд ≈ 1–2 минуты доклада. Если в задании указано число, возьмите его.",
        "🔢 <b>Nechta slayd kerak?</b>\nTanlang yoki 3 dan 30 gacha son yozing. Mo'ljal: bitta slayd ≈ 1–2 daqiqalik ma'ruza. Topshiriqda son ko'rsatilgan bo'lsa, uni oling.",
        "🔢 <b>How many slides do you need?</b>\nChoose or write a number from 3 to 30. Rule of thumb: one slide ≈ 1–2 minutes of talking. If your assignment states a number, use it."),
    "slides_count_bad": ("Напишите число от 3 до 30.", "3 dan 30 gacha son yozing.", "Write a number from 3 to 30."),
    "slides_purpose": ("🎯 <b>Для чего презентация?</b> От этого зависят структура и тон.", "🎯 <b>Taqdimot nima uchun?</b> Tuzilma va ohang shunga bog'liq.",
                       "🎯 <b>What is the presentation for?</b> Structure and tone depend on it."),
    "purpose_defense": ("🎓 Защита работы", "🎓 Ishni himoya qilish", "🎓 Defense of a work"),
    "purpose_talk": ("🗣 Доклад на занятии", "🗣 Darsda ma'ruza", "🗣 Class talk"),
    "purpose_business": ("💼 Бизнес / проект", "💼 Biznes / loyiha", "💼 Business / project"),
    "purpose_school": ("🏫 Для школы", "🏫 Maktab uchun", "🏫 For school"),
    "slides_style": (
        "🎨 <b>Выберите стиль оформления.</b>\n\n▫️ Тема: {topic}\n▫️ Слайдов: {count}\n▫️ Цель: {purpose}\n\n💰 Стоимость: <b>{price} ⭐</b> · баланс: {balance} ⭐\n"
        "Нажатие на стиль запускает создание.",
        "🎨 <b>Dizayn uslubini tanlang.</b>\n\n▫️ Mavzu: {topic}\n▫️ Slaydlar: {count}\n▫️ Maqsad: {purpose}\n\n💰 Narxi: <b>{price} ⭐</b> · balans: {balance} ⭐\n"
        "Uslubni bossangiz, yaratish boshlanadi.",
        "🎨 <b>Choose a design style.</b>\n\n▫️ Topic: {topic}\n▫️ Slides: {count}\n▫️ Purpose: {purpose}\n\n💰 Price: <b>{price} ⭐</b> · balance: {balance} ⭐\n"
        "Tapping a style starts the build."),
    # ---- my works ----
    "works_empty": ("📂 Здесь появятся ваши готовые работы и презентации. Пока ничего нет.", "📂 Bu yerda tayyor ishlaringiz va taqdimotlaringiz paydo bo'ladi. Hozircha hech narsa yo'q.",
                    "📂 Your finished works and presentations will appear here. Nothing yet."),
    "works_title": ("📂 <b>Мои работы</b>\nНажмите, чтобы скачать файл ещё раз:", "📂 <b>Mening ishlarim</b>\nFaylni qayta yuklab olish uchun bosing:",
                    "📂 <b>My works</b>\nTap to download a file again:"),
    "works_gone": ("Файл больше не доступен.", "Fayl endi mavjud emas.", "The file is no longer available."),
}
