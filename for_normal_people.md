# Версия для нормальных людей (без IT-мунспика и скриншотов мелким шрифтом)

---

## Вариант 1 — На русском (для друзей в Telegram / Facebook)

Специально для Сани Соколова и всех нормальных людей — перевожу с программистского на человеческий, без единого скриншота с мелким текстом :)

Представь, что у тебя дома стоит мощный 12-цилиндровый мотор (мой рабочий компьютер), который сейчас круглосуточно пашет на полную катушку по работе. И вот уже **6 лет подряд** два цилиндра из двенадцати крутятся вхолостую на максимальных оборотах день и ночь, просто грея воздух в комнате и мотая счётчик электричества.

Кто жрал эти два цилиндра:
1. **Первый — встроенный «ревизор» от Microsoft.** Четыре дня назад в два часа ночи он пошёл пересчитывать программы на компьютере, заблудился в папках и 100 часов подряд кругами ходил в одну и ту же дверь. Его мы просто выключили и заперли дверь на ключ.
2. **Второй — программа Apple iCloud (которая синхронизирует фотки с айфона на компьютер).** Вот она сводила меня с ума **6 лет**. Закрываешь её — а она через 5 секунд сама запускается заново и снова давит педаль газа в пол.

Раньше, чтобы понять, почему чужая закрытая программа так себя ведёт, нужно было потратить выходные с лупой и паяльником. А сегодня я просто сказал своему ИИ-напарнику: *«Слушай, залезь внутрь и посмотри, чем эта зараза от Apple занимается уже 6 лет?»*

Через 10 минут ИИ выдал диагноз, от которого я смеялся в голос.

Оказывается:
У меня в облаке около **110 тысяч фото и видео**. Программа Apple ведёт у себя на компьютере огромную амбарную книгу (список всех фоток).
Когда-то давно я удалил с телефона **21 старую фотку**. Из-за глупой опечатки программистов Apple в этой амбарной книге напротив этих 21 фоток стёрлись их номера, но осталась пометка: *«Нужно вычеркнуть!»*

И вот что программа Apple делала **каждые 4 секунды на протяжении 6 лет**:
1. Открывала амбарную книгу на 117 тысяч строк.
2. Так как программисты Apple забыли сделать в книге алфавитный указатель (оглавление), курьер **каждые 4 секунды перелистывал все 117 тысяч страниц вручную с первой до последней**.
3. Натыкался на эти 21 пустые строчки в самом начале очереди, пытался вычеркнуть «фотку без номера», не понимал как это сделать, бросал всю стопку, **не пропускал 5 376 новых фоток, которые стояли в очереди сзади**, и через 4 секунды начинал листать всю книгу заново.

Но самое смешное началось, когда мы вычеркнули эти 21 пустые строчки и открыли засов!
Как только в комнату хлынули новые фотки, которые ждали своей очереди 6 лет, выяснилось, что на **каждую** входящую фотку курьер Apple снова перелистывает всю книгу с первой до последней страницы (потому что программист записал вопрос задом наперёд), а иногда пытается приклеить один и тот же уникальный номер сразу на две строчки и падает в обморок.

**Цена этой халтуры:**
* В Калифорнии (Marina del Rey) дорогое электричество. Один этот зависший «курьер» Apple, крутящий процессор и кондиционер 24/7, за 6 лет намотал мне **около $1 000 (тысячи долларов!) за свет** — просто перелистывая 21 пустую строчку каждые 4 секунды.
* А теперь представьте масштаб: такими программами от Apple и Microsoft пользуются **сотни миллионов людей по всему миру**. Люди думают, что у них «постарел ноутбук», потому что он гудит вентилятором и садит батарейку за два часа, а на самом деле в масштабах планеты целая электростанция работает впустую из-за пары забытых строчек кода.

**Чем всё кончилось:**
ИИ прямо внутри этой «амбарной книги» зачеркнул пустые строчки, приклеил три нормальных оглавления (поиск ускорился **от 24 до 1 110 раз!**) и поставил «автовахтёра», который сам исправляет такие опечатки и дубликаты на лету.
Очередь из **5 376 застрявших фотографий** пролетела за пару минут, и программа впервые за 6 лет перестала крутить мотор вхолостую.

**И главная мысль не про компьютеры:**
Вся эта операция заняла 15 минут обычного разговора с ИИ на человеческом языке. Эта «суперспособность» больше не принадлежит узкой касте программистов — сегодня она есть у каждого. Проблема больше не в том, где взять суперспособность, а в том, как догадаться её применить и какой вопрос задать.

---

## Option 2 — In Plain English (Zero Jargon Version)

For my non-tech friends who don't want to read tiny terminal screenshots or database code—here is what actually happened in plain English:

Imagine your desktop computer has a 12-cylinder engine. Lately, I’ve been using all 12 cylinders 24/7 for heavy work. Yet for the last **six years**, two of those cylinders have been revving at 100% redline day and night for no reason—heating up the room, spinning the fans, and running up my electric bill.

One culprit was a built-in Windows background check that got lost in my folders four days ago and spent 100 hours walking in circles. We turned it off.

The second culprit was **Apple’s iCloud Photos app for Windows**. For **six years**, it had been pegging one cylinder at 100% non-stop. If you forced it to close, it would pop right back up five seconds later and floor the gas pedal again.

Normally, figuring out why a closed-source commercial app is misbehaving takes days of digging. Today, I just asked my AI assistant: *"Can you look inside and tell me what on earth this app has been doing for the last six years?"*

Ten minutes later, the AI came back with an explanation that is equal parts hilarious and absurd:

1. I have about **110,000 photos** in iCloud. To keep track of them, the Apple app keeps a giant ledger book on my hard drive with 117,000 entries.
2. Years ago, 21 photos were deleted on my phone. Due to a typo by an Apple programmer, the ID numbers for those 21 deleted entries got erased in the ledger, leaving 21 blank lines marked *"Must be crossed out!"*
3. Because of a second oversight, the programmers forgot to put an alphabetical index in the ledger.
4. So **every 4 seconds for the last 6 years**, the app read all 117,000 entries from page 1 to the end by hand, hit those 21 blank lines at the front of the line, got confused because it couldn't cross out a blank ID, gave up without touching the **5,376 newer photos waiting behind them**, and started reading the entire book all over again 4 seconds later.
5. Even better: the moment we cleared those 21 blank lines and the floodgates opened, we caught the clerk reading the entire 117,000-page book by hand *again* for every single incoming photo (because the lookup question was written backwards) and tripping over duplicate blank lines!

**The Cost of That Typo:**
* Here in Marina del Rey, California, Southern California Edison electricity isn't cheap. Keeping those CPU cores revving at max boost 24/7 (plus the A/C to cool the room) burned roughly **$1,000 of electricity over 6 years** on my desk alone—just to re-read 21 blank lines every 4 seconds.
* Now zoom out: **hundreds of millions of people** run these exact apps every day. Millions of laptops are running hot, draining batteries, and wasting megawatts of power globally because of a handful of overlooked lines of code.

**The Fix & The Takeaway:**
In minutes, the AI crossed out those 21 blank lines in the ledger, added three missing alphabetical indexes (making lookups **24x to 1,110x faster**), and installed automatic rules so the ledger heals itself whenever the app makes those mistakes again. All 5,376 stuck photos synced right through.

The crazy part? I didn't write a single line of code to do it—it took a 15-minute conversation with an AI. That superpower is available to everyone now. The hard part is no longer having the superpower; it's knowing where to point it.
