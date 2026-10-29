"""Texts of the free tools: slides, AI check, file converter (ru, uz, en)."""
TOOLS: dict[str, tuple[str, str, str]] = {
    "btn_slides": ("📊 Слайды", "📊 Slaydlar", "📊 Slides"),
    "btn_detect": ("🕵️ Проверка на ИИ", "🕵️ AI tekshiruvi", "🕵️ AI check"),
    "btn_convert": ("🔁 Конвертер", "🔁 Konvertor", "🔁 Converter"),
    "tool_limit": (
        "Бесплатный лимит на сегодня исчерпан ({n}). Он обновится завтра; у подписчиков лимит втрое больше (/subscribe).",
        "Bugungi bepul limit tugadi ({n}). U ertaga yangilanadi; obunachilarda limit uch barobar ko'p (/subscribe).",
        "Today's free limit is used up ({n}). It resets tomorrow; subscribers get three times more (/subscribe)."),
    # ---- slides ----
    "slides_intro": (
        "📊 <b>Слайды бесплатно</b>\n\nНапишите тему презентации, можно с числом слайдов, например: <i>«Цифровой маркетинг, 12 слайдов»</i>. "
        "Или пришлите файл (.txt, .pdf, .docx), и я сделаю презентацию по нему. Вы получите готовый .pptx для PowerPoint.\n\nОтмена: /cancel",
        "📊 <b>Slaydlar bepul</b>\n\nTaqdimot mavzusini yozing, slaydlar sonini ham ko'rsatish mumkin, masalan: <i>«Raqamli marketing, 12 slayd»</i>. "
        "Yoki fayl (.txt, .pdf, .docx) yuboring, men uning asosida taqdimot qilaman. PowerPoint uchun tayyor .pptx olasiz.\n\nBekor qilish: /cancel",
        "📊 <b>Free slides</b>\n\nSend the presentation topic, optionally with a slide count, e.g. <i>\"Digital marketing, 12 slides\"</i>. "
        "Or send a file (.txt, .pdf, .docx) and I'll build the deck from it. You get a ready .pptx for PowerPoint.\n\nCancel: /cancel"),
    "slides_working": ("⏳ Продумываю структуру, пишу слайды и проверяю качество. Это займёт около минуты…", "⏳ Tuzilmani o'ylab, slaydlarni yozib, sifatni tekshiryapman. Taxminan bir daqiqa…",
                       "⏳ Planning the story, writing the slides and polishing them. About a minute…"),
    "slides_done": (
        "✅ Готово: {n} слайдов. К каждому слайду есть заметки для выступления. Проверьте факты перед защитой.",
        "✅ Tayyor: {n} ta slayd. Har bir slaydga chiqish uchun izohlar bor. Himoyadan oldin faktlarni tekshiring.",
        "✅ Done: {n} slides. Every slide has speaker notes. Check the facts before presenting."),
    "slides_fail": ("Не получилось собрать презентацию. Попробуйте переформулировать тему.", "Taqdimot tayyorlab bo'lmadi. Mavzuni boshqacha yozib ko'ring.",
                    "Could not build the presentation. Try rephrasing the topic."),
    "slides_short": ("Напишите тему подробнее или пришлите файл.", "Mavzuni batafsilroq yozing yoki fayl yuboring.", "Describe the topic in more detail or send a file."),
    "theme_modern": ("🎨 Современный", "🎨 Zamonaviy", "🎨 Modern"),
    "theme_classic": ("🎨 Строгий", "🎨 Klassik", "🎨 Classic"),
    "theme_dark": ("🎨 Тёмный", "🎨 Qorong'i", "🎨 Dark"),
    "slides_restyle": ("Другой стиль той же презентации (без новой генерации):", "Xuddi shu taqdimotning boshqa uslubi (qayta yaratmasdan):",
                       "Another style of the same deck (no new generation):"),
    "slides_old": ("Эта презентация уже недоступна для смены стиля: создайте новую.", "Bu taqdimot uslubini o'zgartirib bo'lmaydi: yangisini yarating.",
                   "This deck can no longer be restyled: create a new one."),
    "stars_btn": ("ℹ️ Как купить Stars", "ℹ️ Stars qanday sotib olinadi", "ℹ️ How to buy Stars"),
    "stars_howto": (
        "⭐ <b>Как купить Telegram Stars</b>\n\n"
        "<b>Способ 1. Прямо при оплате</b>\n"
        "1. Нажмите «⭐ Оплатить» под подпиской.\n"
        "2. В окне счёта нажмите «Оплатить». Если Stars не хватает, Telegram сам предложит докупить нужное количество.\n"
        "3. Выберите способ оплаты (банковская карта, Apple Pay или Google Pay), подтвердите платёж. Stars сразу спишутся, и подписка включится.\n\n"
        "<b>Способ 2. Заранее через настройки</b>\n"
        "1. Откройте Telegram → <b>Настройки</b> → <b>Мои звёзды</b> (My Stars).\n"
        "2. Нажмите <b>Купить звёзды</b> / «Пополнить» и выберите пакет.\n"
        "3. Оплатите, и звёзды появятся на балансе. Потом вернитесь в бот и нажмите «💎 Подписка».\n\n"
        "<b>Способ 3. Через бота @PremiumBot</b>: откройте его, нажмите Start и выберите «Купить звёзды».\n\n"
        "💡 <b>Полезно знать</b>\n"
        "• Если карта не проходит, попробуйте другую карту, Apple Pay или Google Pay.\n"
        "• Цена звёзд может отличаться в зависимости от платформы: на iPhone через App Store обычно дороже, чем через карту на сайте или в Android.\n"
        "• Stars можно получить в подарок от друга: пусть отправит их вам из своего баланса.\n"
        "• Подписка стоит {price} ⭐ на {days} дней. Если оплата прошла, а подписка не включилась, нажмите «🆘 Поддержка».",
        "⭐ <b>Telegram Stars qanday sotib olinadi</b>\n\n"
        "<b>1-usul. To'lov paytida</b>\n"
        "1. Obuna ostidagi «⭐ To'lash» tugmasini bosing.\n"
        "2. Hisob oynasida «To'lash» ni bosing. Stars yetmasa, Telegram yetishmayotgan miqdorni o'zi sotib olishni taklif qiladi.\n"
        "3. To'lov usulini tanlang (bank kartasi, Apple Pay yoki Google Pay) va tasdiqlang. Stars darhol yechiladi va obuna yoqiladi.\n\n"
        "<b>2-usul. Oldindan sozlamalar orqali</b>\n"
        "1. Telegram → <b>Sozlamalar</b> → <b>Mening yulduzlarim</b> (My Stars) bo'limini oching.\n"
        "2. <b>Yulduz sotib olish</b> / «To'ldirish» ni bosing va paketni tanlang.\n"
        "3. To'lang, yulduzlar balansingizda paydo bo'ladi. Keyin botga qayting va «💎 Obuna» ni bosing.\n\n"
        "<b>3-usul. @PremiumBot orqali</b>: uni oching, Start ni bosing va «Yulduz sotib olish» ni tanlang.\n\n"
        "💡 <b>Bilib qo'ying</b>\n"
        "• Karta o'tmasa, boshqa karta, Apple Pay yoki Google Pay ni sinab ko'ring.\n"
        "• Yulduzlar narxi platformaga qarab farq qilishi mumkin: iPhone da App Store orqali odatda qimmatroq.\n"
        "• Yulduzlarni do'stingizdan sovg'a sifatida olish mumkin: ular o'z balansidan sizga yuborsin.\n"
        "• Obuna {days} kunga {price} ⭐ turadi. To'lov o'tgan, lekin obuna yoqilmagan bo'lsa, «🆘 Yordam xizmati» ni bosing.",
        "⭐ <b>How to buy Telegram Stars</b>\n\n"
        "<b>Way 1. Right at checkout</b>\n"
        "1. Tap «⭐ Pay» under the subscription.\n"
        "2. In the invoice window tap «Pay». If you don't have enough Stars, Telegram offers to buy the missing amount.\n"
        "3. Choose a payment method (bank card, Apple Pay or Google Pay) and confirm. The Stars are charged at once and the subscription turns on.\n\n"
        "<b>Way 2. In advance via Settings</b>\n"
        "1. Open Telegram → <b>Settings</b> → <b>My Stars</b>.\n"
        "2. Tap <b>Buy Stars</b> / «Top up» and choose a package.\n"
        "3. Pay, and the stars appear on your balance. Then return to the bot and tap «💎 Subscription».\n\n"
        "<b>Way 3. Via @PremiumBot</b>: open it, tap Start and choose «Buy Stars».\n\n"
        "💡 <b>Good to know</b>\n"
        "• If your card is declined, try another card, Apple Pay or Google Pay.\n"
        "• The price of Stars can differ by platform: on iPhone through the App Store it is usually higher.\n"
        "• You can get Stars as a gift from a friend: they send them from their own balance.\n"
        "• The subscription costs {price} ⭐ for {days} days. If a payment went through but the subscription did not activate, tap «🆘 Support»."),
    # ---- AI check ----
    "detect_intro": (
        "🕵️ <b>Проверка на ИИ</b>\n\nПришлите текст (от {n} знаков) или файл .txt, .pdf, .docx. Я оценю, насколько он похож на машинный, "
        "покажу самые шаблонные фрагменты и подскажу, как сделать работу по-настоящему своей.\n\n"
        "⚠️ Это ориентир, а не приговор: настоящие детекторы (Антиплагиат, Turnitin, GPTZero) работают иначе и могут показать другой результат.\n\nОтмена: /cancel",
        "🕵️ <b>AI tekshiruvi</b>\n\nMatn ({n} belgidan) yoki .txt, .pdf, .docx fayl yuboring. Matn mashinaniki kabi ko'rinish darajasini baholayman, "
        "eng shablon joylarni ko'rsataman va ishni haqiqatan o'zingizniki qilish bo'yicha maslahat beraman.\n\n"
        "⚠️ Bu taxminiy ko'rsatkich, hukm emas: haqiqiy detektorlar (Antiplagiat, Turnitin, GPTZero) boshqacha ishlaydi va boshqa natija chiqarishi mumkin.\n\nBekor qilish: /cancel",
        "🕵️ <b>AI check</b>\n\nSend a text (at least {n} characters) or a .txt, .pdf, .docx file. I'll estimate how machine-like it reads, "
        "show the most generic passages and suggest how to make the work genuinely yours.\n\n"
        "⚠️ This is an orientation, not a verdict: real detectors (Antiplagiat, Turnitin, GPTZero) work differently and may give another result.\n\nCancel: /cancel"),
    "detect_working": ("⏳ Анализирую текст…", "⏳ Matn tahlil qilinmoqda…", "⏳ Analyzing the text…"),
    "detect_short": ("Нужен текст от {n} знаков, иначе оценка будет случайной.", "Kamida {n} belgilik matn kerak, aks holda baho tasodifiy bo'ladi.",
                     "I need at least {n} characters, otherwise the estimate is random."),
    "detect_head": ("🕵️ <b>Результат: {p}% похоже на ИИ</b>\n{verdict}\n", "🕵️ <b>Natija: {p}% AI matniga o'xshaydi</b>\n{verdict}\n",
                    "🕵️ <b>Result: {p}% looks AI-written</b>\n{verdict}\n"),
    "verdict_low": ("Скорее написано человеком.", "Ko'proq inson yozganga o'xshaydi.", "More likely written by a person."),
    "verdict_mid": ("Есть признаки машинного текста.", "Mashina matni belgilari bor.", "There are signs of machine-written text."),
    "verdict_high": ("Текст читается как машинный.", "Matn mashina yozganidek o'qiladi.", "The text reads as machine-written."),
    "detect_stats": (
        "📏 Слов: {words}, предложений: {sentences}, средняя длина предложения: {avg}, разброс длины: {spread}, шаблонных связок на 1000 слов: {conn}.",
        "📏 So'zlar: {words}, gaplar: {sentences}, o'rtacha gap uzunligi: {avg}, uzunlik tarqoqligi: {spread}, 1000 so'zga shablon bog'lovchilar: {conn}.",
        "📏 Words: {words}, sentences: {sentences}, average sentence length: {avg}, length spread: {spread}, stock connectors per 1000 words: {conn}."),
    "detect_signals": ("<b>Что бросается в глаза</b>", "<b>Nimalar ko'zga tashlanadi</b>", "<b>What stands out</b>"),
    "detect_frags": ("<b>Самые шаблонные места</b>", "<b>Eng shablon joylar</b>", "<b>Most generic passages</b>"),
    "detect_advice": ("<b>Как сделать текст своим</b>", "<b>Matnni o'zingiznikiga aylantirish</b>", "<b>How to make it your own</b>"),
    "detect_note": (
        "⚠️ Оценка приблизительная, гарантий не даёт ни один инструмент. Преподаватель оценивает и знание темы: будьте готовы объяснить работу своими словами.",
        "⚠️ Baho taxminiy, hech bir vosita kafolat bermaydi. O'qituvchi mavzuni bilishingizni ham baholaydi: ishni o'z so'zlaringiz bilan tushuntirishga tayyor bo'ling.",
        "⚠️ The estimate is approximate and no tool gives guarantees. Your teacher also judges your knowledge: be ready to explain the work in your own words."),
    "detect_fail": ("Не удалось выполнить анализ. Попробуйте ещё раз.", "Tahlil qilib bo'lmadi. Qayta urinib ko'ring.", "The analysis failed. Please try again."),
    # ---- converter ----
    "convert_intro": (
        "🔁 <b>Конвертер файлов</b>\n\nПришлите файл, и я предложу форматы для конвертации:\n"
        "• .docx, .pdf, .txt, .md, .pptx переводятся друг в друга\n• фото и картинки (.jpg, .png) в PDF\n\n"
        "Сохраняются заголовки, абзацы и списки; сложное оформление, таблицы и картинки внутри документов упрощаются. "
        "PDF-сканы без текста не читаются.\n\nОтмена: /cancel",
        "🔁 <b>Fayl konvertori</b>\n\nFayl yuboring, men konvertatsiya formatlarini taklif qilaman:\n"
        "• .docx, .pdf, .txt, .md, .pptx bir-biriga o'tkaziladi\n• rasmlar (.jpg, .png) PDF ga\n\n"
        "Sarlavhalar, abzaslar va ro'yxatlar saqlanadi; murakkab dizayn, jadvallar va hujjat ichidagi rasmlar soddalashtiriladi. "
        "Matnsiz PDF-skanerlar o'qilmaydi.\n\nBekor qilish: /cancel",
        "🔁 <b>File converter</b>\n\nSend a file and I'll offer the formats to convert it to:\n"
        "• .docx, .pdf, .txt, .md, .pptx convert to each other\n• photos and images (.jpg, .png) to PDF\n\n"
        "Headings, paragraphs and lists are kept; complex layout, tables and images inside documents are simplified. "
        "Scanned PDFs without text cannot be read.\n\nCancel: /cancel"),
    "convert_pick": ("Файл <b>{name}</b> получен. Во что конвертировать?", "<b>{name}</b> fayli qabul qilindi. Qaysi formatga o'tkazamiz?",
                     "Got <b>{name}</b>. Convert to what?"),
    "convert_working": ("⏳ Конвертирую…", "⏳ Konvertatsiya qilinmoqda…", "⏳ Converting…"),
    "convert_done": ("✅ Готово: {name}", "✅ Tayyor: {name}", "✅ Done: {name}"),
    "convert_expired": ("Файл не найден, пришлите его ещё раз.", "Fayl topilmadi, uni qayta yuboring.", "File not found, please send it again."),
    "convert_fail": ("Не удалось конвертировать файл.", "Faylni konvertatsiya qilib bo'lmadi.", "The file could not be converted."),
    "conv_err_unsupported": (
        "Этот формат не поддерживается. Пришлите .docx, .pdf, .txt, .md, .pptx или картинку (.jpg, .png).",
        "Bu format qo'llab-quvvatlanmaydi. .docx, .pdf, .txt, .md, .pptx yoki rasm (.jpg, .png) yuboring.",
        "This format is not supported. Send .docx, .pdf, .txt, .md, .pptx or an image (.jpg, .png)."),
    "conv_err_read": ("Не удалось прочитать файл. Проверьте, что он не повреждён и не защищён паролем.",
                      "Faylni o'qib bo'lmadi. U shikastlanmagan va parol bilan himoyalanmaganini tekshiring.",
                      "The file could not be read. Check that it is not damaged or password-protected."),
    "conv_err_scan": ("В этом PDF нет текста (похоже, это скан). Пришлите PDF с текстом.", "Bu PDF da matn yo'q (skaner bo'lsa kerak). Matnli PDF yuboring.",
                      "This PDF has no text (it looks like a scan). Send a PDF with text."),
    "conv_err_empty": ("В файле нет текста для конвертации.", "Faylda konvertatsiya qilinadigan matn yo'q.", "The file has no text to convert."),
}
