"""Texts of the free tools: slides, AI check, file converter (ru, uz, en)."""
TOOLS: dict[str, tuple[str, str, str]] = {
    "btn_slides": ("📊 Слайды", "📊 Slaydlar", "📊 Slides"),
    "btn_detect": ("🕵️ Проверка на ИИ", "🕵️ AI tekshiruvi", "🕵️ AI check"),
    "btn_convert": ("🔁 Конвертер", "🔁 Konvertor", "🔁 Converter"),
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
    # ---- payment by card transfer ----
    "btn_card_pay": ("💳 Картой Uzcard / Humo", "💳 Uzcard / Humo kartasi bilan", "💳 Pay by Uzcard / Humo card"),
    "btn_provider": ("💳 Click / Payme", "💳 Click / Payme", "💳 Click / Payme"),
    "card_holder_line": ("Получатель: {name}\n", "Qabul qiluvchi: {name}\n", "Recipient: {name}\n"),
    "card_paid_btn": ("✅ Я оплатил", "✅ To'ladim", "✅ I have paid"),
    "card_send": ("Пришлите скриншот или фото чека одним сообщением. Отмена: /cancel",
                  "Chekning skrinshoti yoki rasmini bitta xabarda yuboring. Bekor qilish: /cancel",
                  "Send a screenshot or photo of the receipt in one message. Cancel: /cancel"),
    "card_need_photo": ("Нужен именно скриншот или фото чека (картинкой или файлом).", "Aynan chekning skrinshoti yoki rasmi kerak (rasm yoki fayl ko'rinishida).",
                        "Please send the receipt as a screenshot or photo (image or file)."),
    "card_pending": ("Ваша заявка на проверке, дождитесь ответа администратора.", "Arizangiz tekshiruvda, administrator javobini kuting.",
                     "Your request is being reviewed, please wait for the administrator."),
    "card_rejected": ("❌ Платёж не подтверждён. Если это ошибка, нажмите «🆘 Поддержка» и приложите чек.",
                      "❌ To'lov tasdiqlanmadi. Xato bo'lsa, «🆘 Yordam xizmati» tugmasini bosing va chekni ilova qiling.",
                      "❌ The payment was not confirmed. If this is a mistake, tap «🆘 Support» and attach the receipt."),
    # ---- guide ----
    "guide": (
        "📖 <b>Как пользоваться ботом</b>\n\n"
        "<b>1. Работы и тексты</b>\n"
        "✍️ <b>Писать работу</b>: курсовая, реферат, эссе, план. Напишите тему, объём и требования вуза.\n"
        "🧮 <b>Задачи и код</b>: пришлите условие, получите решение по шагам.\n"
        "📝 <b>Редактор и перевод</b>: проверка текста, рерайт, перевод. Можно прислать файл .txt, .pdf или .docx.\n"
        "🎓 <b>Шпаргалки и экзамен</b>: из конспекта сделаю шпаргалку, а «Вредный преподаватель» зададёт каверзные вопросы, как на защите.\n\n"
        "<b>2. Инструменты</b>\n"
        "📊 <b>Слайды</b>: тема (можно с числом слайдов) или файл, и вы получите готовую презентацию .pptx с заметками для выступления в трёх стилях.\n"
        "🔁 <b>Конвертер</b>: .docx, .pdf, .txt, .md, .pptx переводятся друг в друга, а фото в PDF.\n"
        "🕵️ <b>Проверка на ИИ</b>: оценка текста и советы, как сделать его по-настоящему своим.\n\n"
        "<b>3. Оплата</b>\n"
        "🎁 Бесплатных действий для начала: <b>{free}</b>. Дальше оплата из кошелька в ⭐: вопрос {chat} ⭐, слайды {slides} ⭐, "
        "проверка на ИИ {detect} ⭐, конвертация {convert} ⭐. Если действие не удалось, звёзды возвращаются.\n"
        "💰 <b>Кошелёк</b> пополняется на любую сумму от 1 ⭐. Как купить Stars: /stars\n\n"
        "<b>4. Полезное</b>\n"
        "🧹 <b>Новый диалог</b> очищает память, когда меняете тему.\n"
        "🆘 <b>Поддержка</b>: напишите, если что-то не работает.\n"
        "🌐 <b>Язык</b>: сменить язык бота.\n\n"
        "💡 Чем точнее задача (тема, объём, стандарт оформления, дедлайн), тем лучше результат. Факты и источники в ответах проверяйте сами. "
        "Эту инструкцию можно открыть снова командой /guide.",
        "📖 <b>Botdan qanday foydalaniladi</b>\n\n"
        "<b>1. Ishlar va matnlar</b>\n"
        "✍️ <b>Ish yozish</b>: kurs ishi, referat, esse, reja. Mavzu, hajm va universitet talablarini yozing.\n"
        "🧮 <b>Masala va kod</b>: shartni yuboring, yechimni bosqichma-bosqich oling.\n"
        "📝 <b>Muharrir va tarjima</b>: matnni tekshirish, qayta yozish, tarjima. .txt, .pdf yoki .docx fayl yuborish mumkin.\n"
        "🎓 <b>Shpargalka va imtihon</b>: konspektdan shpargalka qilaman, «Qattiq o'qituvchi» esa himoyadagidek qiyin savollar beradi.\n\n"
        "<b>2. Vositalar</b>\n"
        "📊 <b>Slaydlar</b>: mavzu (slaydlar sonini ham yozish mumkin) yoki fayl, natijada nutq uchun izohli, uch xil uslubdagi tayyor .pptx taqdimot olasiz.\n"
        "🔁 <b>Konvertor</b>: .docx, .pdf, .txt, .md, .pptx bir-biriga, rasmlar esa PDF ga o'tkaziladi.\n"
        "🕵️ <b>AI tekshiruvi</b>: matnni baholash va uni haqiqatan o'zingiznikiga aylantirish bo'yicha maslahatlar.\n\n"
        "<b>3. To'lov</b>\n"
        "🎁 Boshlash uchun bepul harakatlar: <b>{free}</b>. Keyin hamyondan ⭐ bilan to'lanadi: savol {chat} ⭐, slaydlar {slides} ⭐, "
        "AI tekshiruvi {detect} ⭐, konvertatsiya {convert} ⭐. Harakat bajarilmasa, yulduzlar qaytariladi.\n"
        "💰 <b>Hamyon</b> istalgan summaga, 1 ⭐ dan to'ldiriladi. Stars qanday sotib olinadi: /stars\n\n"
        "<b>4. Foydali</b>\n"
        "🧹 <b>Yangi suhbat</b> mavzu o'zgarganda xotirani tozalaydi.\n"
        "🆘 <b>Yordam xizmati</b>: biror narsa ishlamasa yozing.\n"
        "🌐 <b>Til</b>: bot tilini almashtirish.\n\n"
        "💡 Topshiriq qanchalik aniq bo'lsa (mavzu, hajm, rasmiylashtirish standarti, muddat), natija shunchalik yaxshi. Javobdagi fakt va manbalarni o'zingiz tekshiring. "
        "Bu yo'riqnomani /guide buyrug'i bilan qayta ochish mumkin.",
        "📖 <b>How to use the bot</b>\n\n"
        "<b>1. Papers and texts</b>\n"
        "✍️ <b>Write a paper</b>: term paper, report, essay, outline. Send the topic, length and your university's requirements.\n"
        "🧮 <b>Problems & code</b>: send the task and get a step-by-step solution.\n"
        "📝 <b>Editor & translation</b>: proofreading, rewriting, translation. You can send a .txt, .pdf or .docx file.\n"
        "🎓 <b>Cheat sheets & exam</b>: I turn notes into a cheat sheet, and the «Tough Professor» asks tricky questions like at a defense.\n\n"
        "<b>2. Tools</b>\n"
        "📊 <b>Slides</b>: a topic (optionally with a slide count) or a file, and you get a ready .pptx deck with speaker notes in three styles.\n"
        "🔁 <b>Converter</b>: .docx, .pdf, .txt, .md, .pptx convert to each other, and photos to PDF.\n"
        "🕵️ <b>AI check</b>: an estimate of a text plus tips to make it genuinely yours.\n\n"
        "<b>3. Payment</b>\n"
        "🎁 Free actions to start with: <b>{free}</b>. After that you pay from the wallet in ⭐: a question {chat} ⭐, slides {slides} ⭐, "
        "AI check {detect} ⭐, conversion {convert} ⭐. If an action fails, the Stars are returned.\n"
        "💰 The <b>Wallet</b> tops up any amount from 1 ⭐. How to buy Stars: /stars\n\n"
        "<b>4. Handy</b>\n"
        "🧹 <b>New chat</b> clears the memory when you change the topic.\n"
        "🆘 <b>Support</b>: write to us if something does not work.\n"
        "🌐 <b>Language</b>: change the bot's language.\n\n"
        "💡 The more precise the task (topic, length, formatting standard, deadline), the better the result. Check the facts and sources in answers yourself. "
        "You can open this guide again with /guide."),
    # ---- wallet ----
    "truncated": (
        "\n\n…ответ получился очень длинным и был обрезан. Напишите «продолжи», чтобы получить следующую часть (это отдельный вопрос по цене кошелька).",
        "\n\n…javob juda uzun bo'lib, qisqartirildi. Keyingi qismini olish uchun «davom et» deb yozing (bu hamyon narxidagi alohida savol).",
        "\n\n…the answer was very long and got cut. Write «continue» to get the next part (it counts as a separate question at the wallet price)."),
    "btn_sub": ("💰 Кошелёк", "💰 Hamyon", "💰 Wallet"),
    "wallet_text": (
        "💰 <b>Ваш кошелёк</b>\n\nБаланс: <b>{balance} ⭐</b> (хватит примерно на {n} вопросов)\n🎁 Бесплатных действий осталось: <b>{free}</b>\n\n"
        "<b>Стоимость действий</b>\n• вопрос ассистенту: {chat} ⭐\n• презентация: {slides} ⭐\n• проверка на ИИ: {detect} ⭐\n• конвертация файла: {convert} ⭐\n\n"
        "Пополнить можно на любую сумму, начиная с 1 ⭐: выберите вариант или нажмите «Другая сумма».",
        "💰 <b>Sizning hamyoningiz</b>\n\nBalans: <b>{balance} ⭐</b> (taxminan {n} ta savolga yetadi)\n🎁 Qolgan bepul harakatlar: <b>{free}</b>\n\n"
        "<b>Harakatlar narxi</b>\n• yordamchiga savol: {chat} ⭐\n• taqdimot: {slides} ⭐\n• AI tekshiruvi: {detect} ⭐\n• faylni konvertatsiya qilish: {convert} ⭐\n\n"
        "Hamyonni istalgan summaga to'ldirish mumkin, 1 ⭐ dan boshlab: variantni tanlang yoki «Boshqa summa» ni bosing.",
        "💰 <b>Your wallet</b>\n\nBalance: <b>{balance} ⭐</b> (enough for about {n} questions)\n🎁 Free actions left: <b>{free}</b>\n\n"
        "<b>Cost of actions</b>\n• a question to the assistant: {chat} ⭐\n• a presentation: {slides} ⭐\n• an AI check: {detect} ⭐\n• a file conversion: {convert} ⭐\n\n"
        "You can top up any amount, starting from 1 ⭐: pick an option or tap «Other amount»."),
    "free_line": ("🎁 бесплатное действие, осталось: {left}", "🎁 bepul harakat, qoldi: {left}", "🎁 free action, left: {left}"),
    "top_other": ("✏️ Другая сумма", "✏️ Boshqa summa", "✏️ Other amount"),
    "top_ask": ("Напишите, на сколько звёзд пополнить кошелёк: любое целое число от 1 до {max}. Отмена: /cancel",
                "Hamyonni necha yulduzga to'ldirishni yozing: 1 dan {max} gacha istalgan butun son. Bekor qilish: /cancel",
                "Write how many Stars to add to your wallet: any whole number from 1 to {max}. Cancel: /cancel"),
    "top_bad": ("Введите целое число от 1 до {max}.", "1 dan {max} gacha butun son kiriting.", "Enter a whole number from 1 to {max}."),
    "top_title": ("Пополнение кошелька на {n} ⭐", "Hamyonni {n} ⭐ ga to'ldirish", "Wallet top-up: {n} ⭐"),
    "top_desc": ("Звёзды зачисляются на ваш баланс в боте и тратятся на действия.", "Yulduzlar botdagi balansingizga o'tadi va harakatlarga sarflanadi.",
                 "The Stars are added to your balance in the bot and spent on actions."),
    "top_label": ("Пополнение {n} ⭐", "{n} ⭐ to'ldirish", "Top-up {n} ⭐"),
    "top_ok": ("✅ Кошелёк пополнен на {n} ⭐. Баланс: {balance} ⭐.", "✅ Hamyon {n} ⭐ ga to'ldirildi. Balans: {balance} ⭐.",
               "✅ Wallet topped up by {n} ⭐. Balance: {balance} ⭐."),
    "need_funds": ("Недостаточно звёзд: действие стоит {price} ⭐, на балансе {balance} ⭐. Пополните кошелёк на любую сумму:",
                   "Yulduz yetarli emas: harakat narxi {price} ⭐, balansda {balance} ⭐. Hamyonni istalgan summaga to'ldiring:",
                   "Not enough Stars: the action costs {price} ⭐, your balance is {balance} ⭐. Top up any amount:"),
    "top_missing": ("⭐ Пополнить на {n}", "⭐ {n} ga to'ldirish", "⭐ Top up {n}"),
    "spent_line": ("−{n} ⭐ · баланс: {balance} ⭐", "−{n} ⭐ · balans: {balance} ⭐", "−{n} ⭐ · balance: {balance} ⭐"),
    "refunded": ("Звёзды за этот запрос вам вернулись.", "Bu so'rov uchun yulduzlar qaytarildi.", "The Stars for this request were returned to you."),
    "granted": ("💰 Вам начислено {n} ⭐. Баланс: {balance} ⭐.", "💰 Sizga {n} ⭐ berildi. Balans: {balance} ⭐.", "💰 You received {n} ⭐. Balance: {balance} ⭐."),
    "paysupport": (
        "💬 <b>Вопросы по оплате.</b> Если оплата прошла, а звёзды не зачислились, или нужно вернуть платёж, "
        "нажмите «🆘 Поддержка» и сообщите ID платежа из чата с чеком.",
        "💬 <b>To'lov bo'yicha savollar.</b> To'lov o'tgan, lekin yulduzlar tushmagan bo'lsa yoki to'lovni qaytarish kerak bo'lsa, "
        "«🆘 Yordam xizmati» tugmasini bosing va chekdagi to'lov ID sini yozing.",
        "💬 <b>Payment questions.</b> If a payment went through but the Stars were not added, or you need a refund, "
        "tap «🆘 Support» and send the payment ID from the receipt chat."),
    "stars_howto": (
        "⭐ <b>Как купить Telegram Stars</b>\n\n"
        "<b>Способ 1. Прямо при пополнении</b>\n"
        "1. Откройте «💰 Кошелёк» и выберите сумму.\n"
        "2. В окне счёта нажмите «Оплатить». Если Stars не хватает, Telegram сам предложит докупить нужное количество.\n"
        "3. Выберите способ оплаты (банковская карта, Apple Pay или Google Pay) и подтвердите. Звёзды сразу зачислятся в кошелёк.\n\n"
        "<b>Способ 2. Заранее через настройки</b>\n"
        "1. Откройте Telegram → <b>Настройки</b> → <b>Мои звёзды</b> (My Stars).\n"
        "2. Нажмите <b>Купить звёзды</b> / «Пополнить» и выберите пакет.\n"
        "3. Оплатите, и звёзды появятся на балансе Telegram. Потом вернитесь в бот и пополните кошелёк.\n\n"
        "<b>Способ 3. Через бота @PremiumBot</b>: откройте его, нажмите Start и выберите «Купить звёзды».\n\n"
        "💡 <b>Полезно знать</b>\n"
        "• Если карта не проходит, попробуйте другую карту, Apple Pay или Google Pay.\n"
        "• Цена звёзд зависит от платформы: на iPhone через App Store обычно дороже.\n"
        "• Звёзды можно получить в подарок от друга.\n"
        "• Если оплата прошла, а звёзды не зачислились, нажмите «🆘 Поддержка».",
        "⭐ <b>Telegram Stars qanday sotib olinadi</b>\n\n"
        "<b>1-usul. Hamyonni to'ldirishda</b>\n"
        "1. «💰 Hamyon» ni oching va summani tanlang.\n"
        "2. Hisob oynasida «To'lash» ni bosing. Stars yetmasa, Telegram yetishmayotgan miqdorni o'zi sotib olishni taklif qiladi.\n"
        "3. To'lov usulini tanlang (bank kartasi, Apple Pay yoki Google Pay) va tasdiqlang. Yulduzlar darhol hamyonga tushadi.\n\n"
        "<b>2-usul. Oldindan sozlamalar orqali</b>\n"
        "1. Telegram → <b>Sozlamalar</b> → <b>Mening yulduzlarim</b> (My Stars) bo'limini oching.\n"
        "2. <b>Yulduz sotib olish</b> / «To'ldirish» ni bosing va paketni tanlang.\n"
        "3. To'lang, yulduzlar Telegram balansida paydo bo'ladi. Keyin botga qayting va hamyonni to'ldiring.\n\n"
        "<b>3-usul. @PremiumBot orqali</b>: uni oching, Start ni bosing va «Yulduz sotib olish» ni tanlang.\n\n"
        "💡 <b>Bilib qo'ying</b>\n"
        "• Karta o'tmasa, boshqa karta, Apple Pay yoki Google Pay ni sinab ko'ring.\n"
        "• Yulduzlar narxi platformaga bog'liq: iPhone da App Store orqali odatda qimmatroq.\n"
        "• Yulduzlarni do'stingizdan sovg'a sifatida olish mumkin.\n"
        "• To'lov o'tgan, lekin yulduzlar tushmagan bo'lsa, «🆘 Yordam xizmati» ni bosing.",
        "⭐ <b>How to buy Telegram Stars</b>\n\n"
        "<b>Way 1. Right when topping up</b>\n"
        "1. Open «💰 Wallet» and choose an amount.\n"
        "2. In the invoice window tap «Pay». If you don't have enough Stars, Telegram offers to buy the missing amount.\n"
        "3. Choose a payment method (bank card, Apple Pay or Google Pay) and confirm. The Stars land in your wallet at once.\n\n"
        "<b>Way 2. In advance via Settings</b>\n"
        "1. Open Telegram → <b>Settings</b> → <b>My Stars</b>.\n"
        "2. Tap <b>Buy Stars</b> / «Top up» and choose a package.\n"
        "3. Pay, and the stars appear on your Telegram balance. Then return to the bot and top up your wallet.\n\n"
        "<b>Way 3. Via @PremiumBot</b>: open it, tap Start and choose «Buy Stars».\n\n"
        "💡 <b>Good to know</b>\n"
        "• If your card is declined, try another card, Apple Pay or Google Pay.\n"
        "• The price of Stars depends on the platform: on iPhone through the App Store it is usually higher.\n"
        "• You can get Stars as a gift from a friend.\n"
        "• If a payment went through but the Stars were not added, tap «🆘 Support»."),
    "card_ask": ("Сколько звёзд хотите купить? Напишите любое целое число от 1 (курс: 1 ⭐ = {rate} сум). Отмена: /cancel",
                 "Necha yulduz sotib olmoqchisiz? 1 dan boshlab istalgan butun son yozing (kurs: 1 ⭐ = {rate} so'm). Bekor qilish: /cancel",
                 "How many Stars do you want to buy? Write any whole number from 1 (rate: 1 ⭐ = {rate} UZS). Cancel: /cancel"),
    "card_text": (
        "💳 <b>Пополнение переводом на карту</b>\n\n"
        "Нужно перевести: <b>{amount} сум</b>, на кошелёк придёт <b>{stars} ⭐</b>\n"
        "Карта: <code>{card}</code>\n{holder}\n"
        "1. Переведите ровно эту сумму через Click, Payme, Paynet или приложение вашего банка.\n"
        "2. Нажмите «✅ Я оплатил» и пришлите скриншот или фото чека.\n"
        "3. Администратор проверит платёж и зачислит звёзды, обычно в течение нескольких часов.",
        "💳 <b>Kartaga o'tkazma orqali to'ldirish</b>\n\n"
        "O'tkazish kerak: <b>{amount} so'm</b>, hamyonga <b>{stars} ⭐</b> tushadi\n"
        "Karta: <code>{card}</code>\n{holder}\n"
        "1. Aynan shu summani Click, Payme, Paynet yoki bank ilovangiz orqali o'tkazing.\n"
        "2. «✅ To'ladim» tugmasini bosing va chekning skrinshoti yoki rasmini yuboring.\n"
        "3. Administrator to'lovni tekshirib, yulduzlarni o'tkazadi, odatda bir necha soat ichida.",
        "💳 <b>Top-up by card transfer</b>\n\n"
        "Transfer: <b>{amount} UZS</b>, your wallet gets <b>{stars} ⭐</b>\n"
        "Card: <code>{card}</code>\n{holder}\n"
        "1. Transfer exactly this amount via Click, Payme, Paynet or your bank app.\n"
        "2. Tap «✅ I have paid» and send a screenshot or photo of the receipt.\n"
        "3. An administrator checks the payment and adds the Stars, usually within a few hours."),
    "card_received": ("✅ Чек получен, заявка №{id}. Администратор проверит платёж и зачислит звёзды. Я напишу вам здесь.",
                      "✅ Chek qabul qilindi, №{id} ariza. Administrator to'lovni tekshirib, yulduzlarni o'tkazadi. Sizga shu yerda yozaman.",
                      "✅ Receipt received, request #{id}. An administrator will check the payment and add the Stars. I will message you here."),
    "card_approved": ("✅ Платёж подтверждён! Зачислено {stars} ⭐. Баланс: {balance} ⭐.", "✅ To'lov tasdiqlandi! {stars} ⭐ o'tkazildi. Balans: {balance} ⭐.",
                      "✅ Payment confirmed! {stars} ⭐ added. Balance: {balance} ⭐."),
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
