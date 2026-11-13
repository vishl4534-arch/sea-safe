# Place names for native-speaker review

Every Kannada and Arabic place name in the app, in one list.

**Two columns per harbour:**
- **On screen** is the short name the app shows. It lives in `translations/kn.json` or `translations/ar.json` under `place.<id>`.
- **Full harbour name** is the longer form, for reference.

**What \* means:** a descriptive Arabic name that we wrote ourselves; it is not an official or sourced name. Please confirm or correct each one.

Please also review the rest of `translations/kn.json` and `translations/ar.json`, which hold all the interface text. Both files are drafts.

## Karnataka (Kannada)

Most spellings come from OpenStreetMap `name:kn` tags or Kannada Wikipedia.

| id | English | On screen (Kannada) | Full harbour name (Kannada) | Source of spelling |
|---|---|---|---|---|
| mangaluru | Mangaluru (Bunder) | ಮಂಗಳೂರು | ಮಂಗಳೂರು ಮೀನುಗಾರಿಕಾ ಬಂದರು | OSM `name:kn` or Kannada Wikipedia |
| malpe | Malpe | ಮಲ್ಪೆ | ಮಲ್ಪೆ ಬಂದರು | OSM `name:kn` |
| gangolli | Gangolli | ಗಂಗೊಳ್ಳಿ | ಗಂಗೊಳ್ಳಿ ಮೀನುಗಾರಿಕಾ ಬಂದರು | OSM `name:kn` or Kannada Wikipedia |
| bhatkal | Bhatkal | ಭಟ್ಕಳ | ಭಟ್ಕಳ ಮೀನುಗಾರಿಕಾ ಬಂದರು | OSM `name:kn` or Kannada Wikipedia |
| honnavar | Honnavar | ಹೊನ್ನಾವರ | ಹೊನ್ನಾವರ ಮೀನುಗಾರಿಕಾ ಬಂದರು | OSM `name:kn` or Kannada Wikipedia |
| tadri | Tadri (Tadadi) | ತದಡಿ | ತದಡಿ ಮೀನುಗಾರಿಕಾ ಬಂದರು | OSM `name:kn` |
| belekeri | Belekeri | ಬೇಲೇಕೇರಿ | ಬೇಲೇಕೇರಿ ಮೀನುಗಾರಿಕಾ ಬಂದರು | OSM `name:kn` |
| karwar | Karwar (Baithkol) | ಕಾರವಾರ | ಕಾರವಾರ ಬಂದರು | OSM `name:kn` |

**Region name:** ಕರ್ನಾಟಕ ಕರಾವಳಿ (Karnataka coast).

## UAE (Arabic)

| id | English | On screen (Arabic) | Full harbour name (Arabic) | Source of spelling |
|---|---|---|---|---|
| abu_dhabi_mina_zayed | Abu Dhabi – Mina Zayed | أبوظبي – ميناء زايد | سوق السمك – ميناء زايد | common form, please check |
| dubai_umm_suqeim | Dubai – Umm Suqeim | دبي – أم سقيم | ميناء الصيد في أم سقيم\* | descriptive |
| dubai_al_hamriya | Dubai – Al Hamriya | دبي – ميناء الحمرية | ميناء الحمرية | common form, please check |
| ajman | Ajman | عجمان | سوق السمك عجمان | common form, please check |
| umm_al_quwain | Umm Al Quwain (Al Naqqa / Al Meydan port) | أم القيوين | ميناء مرسى الميدان | Emarat Al Youm (2019) |
| rak_al_rams | Ras Al Khaimah – Al Rams | رأس الخيمة – الرمس | ميناء الرمس | common form, please check |
| dibba_al_hisn | Dibba Al-Hisn | دبا الحصن | ميناء دبا الحصن | common form, please check |
| khor_fakkan | Khor Fakkan | خورفكان | ميناء الصيادين في خورفكان\* | descriptive |

**Region name:** ساحل الإمارات (UAE coast).

**Switched off, not shown in the app:**

| id | English | On screen (Arabic) | Full harbour name (Arabic) | Note |
|---|---|---|---|---|
| fujairah | Fujairah (Al Rughaylat) | الفجيرة | ميناء الرغيلات | Fishermen's port not confirmed |
| dubai_jumeirah | Dubai – Jumeirah | دبي – جميرا | ميناء صيد جميرا | Spare harbour, only used if the list drops below seven |

## "From" forms (whole phrases, please check each one)

Templates never attach a suffix to a place name. Each "from X" phrase is stored whole as `place_from.<id>`.
These phrases appear in the line about the weather point ("3.2 km from Malpe") and in the example question.

| id | Kannada name | Kannada "from" form | Arabic name | Arabic "from" form |
|---|---|---|---|---|
| map_point (a tapped point, no harbour) | ನೀವು ಆಯ್ಕೆ ಮಾಡಿದ ಜಾಗ | ಈ ಜಾಗದಿಂದ | النقطة التي اخترتها | من هذه النقطة |
| mangaluru | ಮಂಗಳೂರು | ಮಂಗಳೂರಿನಿಂದ | | |
| malpe | ಮಲ್ಪೆ | ಮಲ್ಪೆಯಿಂದ | | |
| gangolli | ಗಂಗೊಳ್ಳಿ | ಗಂಗೊಳ್ಳಿಯಿಂದ | | |
| bhatkal | ಭಟ್ಕಳ | ಭಟ್ಕಳದಿಂದ | | |
| honnavar | ಹೊನ್ನಾವರ | ಹೊನ್ನಾವರದಿಂದ | | |
| tadri | ತದಡಿ | ತದಡಿಯಿಂದ | | |
| belekeri | ಬೇಲೇಕೇರಿ | ಬೇಲೇಕೇರಿಯಿಂದ | | |
| karwar | ಕಾರವಾರ | ಕಾರವಾರದಿಂದ | | |
| abu_dhabi_mina_zayed | | | أبوظبي – ميناء زايد | من أبوظبي – ميناء زايد |
| dubai_umm_suqeim | | | دبي – أم سقيم | من دبي – أم سقيم |
| dubai_al_hamriya | | | دبي – ميناء الحمرية | من دبي – ميناء الحمرية |
| ajman | | | عجمان | من عجمان |
| umm_al_quwain | | | أم القيوين | من أم القيوين |
| rak_al_rams | | | رأس الخيمة – الرمس | من رأس الخيمة – الرمس |
| dibba_al_hisn | | | دبا الحصن | من دبا الحصن |
| khor_fakkan | | | خورفكان | من خورفكان |

## Other names people say (aliases, new 12 Nov 2026, please check)

These are in `config/app.yaml` under each harbour's `aliases`. The chat uses them to know which harbour a question means,
and the voice sends them to speech-to-text so it hears them right. Please check the Kannada and Arabic spellings, and add
any name local fishers really use.

| id | Kannada / Arabic aliases | Latin aliases |
|---|---|---|
| mangaluru | ಮಂಗಳೂರ, ಬಂದರ್ | Mangalore, Bunder, Old Port, Mangaluru Bunder |
| malpe | ಉಡುಪಿ | Udupi, Malpe Bunder |
| gangolli | ಕುಂದಾಪುರ, ಕುಂದಾಪುರದ, ಗಂಗೊಳ್ಳಿ | Kundapura, Kundapur, Coondapoor, Gangoli, Gangolly |
| bhatkal | ಭಟ್ಕಳ | Bhatkala |
| honnavar | ಹೊನ್ನಾವರ | Honavar, Honnavara |
| tadri | ತದ್ರಿ, ಕುಮಟಾ | Tadadi, Tadri port, Kumta |
| belekeri | ಅಂಕೋಲಾ, ಬೆಲೆಕೇರಿ | Belikeri, Belekere, Ankola |
| karwar | ಬೈತ್ಕೋಲ್ | Baithkol, Baitkol, Karawara |
| abu_dhabi_mina_zayed | ابوظبي، ميناء زايد | Abu Dhabi, Mina Zayed |
| dubai_umm_suqeim | ام سقيم | Umm Suqeim, Umm Suqueim |
| dubai_al_hamriya | الحمرية | Hamriya, Hamriyah, Deira |
| ajman | | Ajman creek |
| umm_al_quwain | ام القيوين | UAQ, Umm al Qaiwain, Al Naqqa, Al Meydan, Al Maidan |
| rak_al_rams | راس الخيمة | Ras Al Khaimah, RAK, Al Rams, Rams |
| dibba_al_hisn | دبا | Dibba, Diba |
| khor_fakkan | خور فكان | Khorfakkan, Khor Fakan |

**The one question the chat asks** (`chat.ask_place`), please check:
- kn: ನಾನು ಒಂದು ಬಂದರು ಮತ್ತು ಒಂದು ಸಮಯಕ್ಕೆ ಸಮುದ್ರದ ಸ್ಥಿತಿ ಪರಿಶೀಲಿಸಬಲ್ಲೆ. ಯಾವ ಬಂದರಿನಿಂದ ಹೊರಡಬೇಕು? {places}.
- ar: أستطيع فحص البحر لميناء واحد ووقت واحد. من أي ميناء تريد الانطلاق؟ {places}.

## Not shown to users

`kn.json` keeps the UAE harbour names in English, and `ar.json` keeps the Karnataka harbour names in English. Those language and region pairs are never shown together, so they need no review.

## Spoken answers and voice (new, 12 Nov 2026)

These sentences are spoken aloud by the voice, or shown on the voice buttons. Please check them as speech: do they sound natural when heard, not only when read?

The voices are the following. Please listen to each one; the ids are in `config/app.yaml` under `voice.languages`.
- **Kannada:** Krishna Priya M, a Kannada news anchor.
- **Arabic:** Heba Mansuri, a Saudi Gulf customer-care voice.

| lang | key | text |
|---|---|---|
| kn | `say.disclaimer` | ಇದು ಮುನ್ಸೂಚನೆ, ಖಾತರಿ ಅಲ್ಲ, ಆದ್ದರಿಂದ ಅಧಿಕೃತ ಎಚ್ಚರಿಕೆಗಳನ್ನೂ ನೋಡಿ. ಸುರಕ್ಷಿತವಾಗಿರಿ. |
| kn | `say.not_heard` | ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಕೇಳಿಸಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮೈಕ್ ಒತ್ತಿ ಮತ್ತೆ ಹೇಳಿ. |
| kn | `say.replay` | ಇದು {date} ರ ಹವಾಮಾನದ ಮರುಪ್ರದರ್ಶನ. |
| kn | `say.safe_summary` | ಅಲೆಗಳು {wave} ಮೀಟರ್ ವರೆಗೆ, ಗಾಳಿ {wind} ಮತ್ತು ಹಠಾತ್ ಬಿರುಗಾಳಿ {gust} ಕಿಲೋಮೀಟರ್ ಪ್ರತಿ ಗಂಟೆಗೆ, ಎಲ್ಲವೂ ಎಚ್ಚರಿಕೆಯ ಮಿತಿಗಿಂತ ಕಡಿಮೆ. |
| kn | `say.trip_assumed` | ಪ್ರಯಾಣ {hours} ಗಂಟೆ ಎಂದು ಊಹಿಸಿದ್ದೇನೆ, ನಿಮ್ಮದು ಬೇರೆ ಇದ್ದರೆ ಹೇಳಿ. |
| kn | `say.unit.km/h` | ಕಿಲೋಮೀಟರ್ ಪ್ರತಿ ಗಂಟೆಗೆ |
| kn | `say.unit.m` | ಮೀಟರ್ |
| kn | `say.unit.s` | ಸೆಕೆಂಡು |
| kn | `ui.listen` | ಕೇಳಿ |
| kn | `ui.mic_start` | ಒತ್ತಿ ಮಾತನಾಡಿ |
| kn | `ui.mic_stop` | ನಿಲ್ಲಿಸಲು ಒತ್ತಿ |
| kn | `ui.voice_working` | ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಕೇಳಲಾಗುತ್ತಿದೆ… |
| kn | `voice.mic_denied` | ಮೈಕ್‌ಗೆ ಅನುಮತಿ ಇಲ್ಲ. ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಅನುಮತಿ ನೀಡಿ, ಅಥವಾ ಪ್ರಶ್ನೆಯನ್ನು ಬರೆಯಿರಿ. |
| kn | `voice.unavailable` | ಧ್ವನಿ ಈಗ ಕೆಲಸ ಮಾಡುತ್ತಿಲ್ಲ. ಬರೆದ ಉತ್ತರ ಪರದೆಯ ಮೇಲಿದೆ. |
| ar | `say.disclaimer` | هذه توقعات وليست وعداً، لذلك تحقّق من التحذيرات الرسمية أيضاً. سلامتك. |
| ar | `say.not_heard` | لم أسمع سؤالاً. اضغط على الميكروفون وحاول مرة أخرى من فضلك. |
| ar | `say.replay` | هذه إعادة عرض لطقس يوم {date}. |
| ar | `say.safe_summary` | الأمواج حتى {wave} متر، والرياح {wind} والهبّات {gust} كيلومتر في الساعة، كلها أقل من حدود الحذر. |
| ar | `say.trip_assumed` | افترضتُ رحلة مدتها {hours} ساعات، أخبرني إذا كانت رحلتك مختلفة. |
| ar | `say.unit.km/h` | كيلومتر في الساعة |
| ar | `say.unit.m` | متر |
| ar | `say.unit.s` | ثانية |
| ar | `ui.listen` | استمع |
| ar | `ui.mic_start` | اضغط وتكلّم |
| ar | `ui.mic_stop` | اضغط للإيقاف |
| ar | `ui.voice_working` | جارٍ الاستماع إلى سؤالك… |
| ar | `voice.mic_denied` | الميكروفون غير مسموح. اسمح به في المتصفح، أو اكتب سؤالك. |
| ar | `voice.unavailable` | الصوت لا يعمل الآن. الإجابة المكتوبة على الشاشة. |

### Conversational spoken answers (13 Nov 2026, please check as speech)

The voice now talks like a person: it says the question back with the verdict, joins the reasons with
"note / also / and", says when they would be back, and ends with "stay safe". No filler words. These are all the
sentences it is built from; please check that they sound natural when heard, and fix anything a fisher would not say.
The openers (`say.opener.*`) are picked by code in turn: please suggest better everyday words if these sound odd.
Samples: `docs/voice-samples/`.

| lang | key | text |
|---|---|---|
| kn | `say.disclaimer` | ಇದು ಮುನ್ಸೂಚನೆ, ಖಾತರಿ ಅಲ್ಲ, ಆದ್ದರಿಂದ ಅಧಿಕೃತ ಎಚ್ಚರಿಕೆಗಳನ್ನೂ ನೋಡಿ. ಸುರಕ್ಷಿತವಾಗಿರಿ. |
| kn | `say.replay` | ಇದು {date} ರ ಹವಾಮಾನದ ಮರುಪ್ರದರ್ಶನ. |
| kn | `say.trip_assumed` | ಪ್ರಯಾಣ {hours} ಗಂಟೆ ಎಂದು ಊಹಿಸಿದ್ದೇನೆ, ನಿಮ್ಮದು ಬೇರೆ ಇದ್ದರೆ ಹೇಳಿ. |
| kn | `say.safe_summary` | ಅಲೆಗಳು {wave} ಮೀಟರ್ ವರೆಗೆ, ಗಾಳಿ {wind} ಮತ್ತು ಹಠಾತ್ ಬಿರುಗಾಳಿ {gust} ಕಿಲೋಮೀಟರ್ ಪ್ರತಿ ಗಂಟೆಗೆ, ಎಲ್ಲವೂ ಎಚ್ಚರಿಕೆಯ ಮಿತಿಗಿಂತ ಕಡಿಮೆ. |
| kn | `say.reason.unsafe` | {lead} {param} {at} {value} {unit} ವರೆಗೆ, ಅಸುರಕ್ಷಿತ ಮಿತಿ ತಲುಪಿದೆ. |
| kn | `say.reason.caution` | {lead} {param} {at} {value} {unit} ವರೆಗೆ, ಎಚ್ಚರಿಕೆಯ ಮಿತಿ ದಾಟಿದೆ. |
| kn | `say.reason.near` | {lead} {param} {at} {value} {unit} ವರೆಗೆ, ಎಚ್ಚರಿಕೆಯ ಮಿತಿಗೆ ಹತ್ತಿರ. |
| kn | `say.reason.caution_below` | {lead} {param} {at} ಕೇವಲ {value} {unit}, ಎಚ್ಚರಿಕೆಯ ಮಿತಿಗಿಂತ ಕಡಿಮೆ. |
| kn | `say.reason.near_below` | {lead} {param} {at} ಕೇವಲ {value} {unit}, ಎಚ್ಚರಿಕೆಯ ಮಿತಿಗೆ ಹತ್ತಿರ. |
| kn | `say.reason.thunderstorm` | {at} ಗುಡುಗು ಸಹಿತ ಮಳೆ ಬರಬಹುದು. |
| kn | `say.reason.missing` | {at} {param} ಮಾಹಿತಿ ಇಲ್ಲ, ಆದ್ದರಿಂದ ಸುರಕ್ಷಿತ ಎನ್ನಲಾಗದು. |
| kn | `say.reason.beyond_window` | ನಿಮ್ಮ ಪ್ರಯಾಣದ ಒಂದು ಭಾಗ ನಮ್ಮ ಮುನ್ಸೂಚನೆಯ ಅವಧಿಯನ್ನು ಮೀರುತ್ತದೆ. |
| kn | `say.advice.SAFE` | ಸಣ್ಣ ದೋಣಿಗೆ ಸಮುದ್ರ ಸಾಕಷ್ಟು ಶಾಂತವಾಗಿ ಕಾಣುತ್ತಿದೆ. |
| kn | `say.advice.CAUTION` | ಸಮುದ್ರದಲ್ಲಿ ಜಾಗ್ರತೆಯಿಂದಿರಿ. |
| kn | `say.advice.UNSAFE` | ದಯವಿಟ್ಟು ಸಣ್ಣ ದೋಣಿಯಲ್ಲಿ ಹೋಗಬೇಡಿ. |
| kn | `say.opener.0` | ಸರಿ |
| kn | `say.opener.1` | ಆಯ್ತು |
| kn | `say.opener.2` | ಓಕೆ |
| kn | `say.verdict_line.SAFE` | {opener}, {place_from} {day} {time} ಹೊರಟರೆ: ಸುರಕ್ಷಿತವಾಗಿ ಕಾಣುತ್ತಿದೆ. |
| kn | `say.verdict_line.CAUTION` | {opener}, {place_from} {day} {time} ಹೊರಟರೆ: ಎಚ್ಚರಿಕೆ. |
| kn | `say.verdict_line.UNSAFE` | {opener}, {place_from} {day} {time} ಹೊರಟರೆ: ಅಸುರಕ್ಷಿತ. |
| kn | `say.lead.first` | ಗಮನಿಸಿ: |
| kn | `say.lead.middle` | ಜೊತೆಗೆ |
| kn | `say.lead.last` | ಮತ್ತು |
| kn | `say.param.wave_height` | ಅಲೆಗಳು |
| kn | `say.param.wind_speed` | ಗಾಳಿ |
| kn | `say.param.wind_gusts` | ಹಠಾತ್ ಬಿರುಗಾಳಿ |
| kn | `say.param.visibility` | ಗೋಚರತೆ |
| kn | `say.back` | ನೀವು {time} ಹಿಂತಿರುಗುತ್ತೀರಿ. |
| kn | `say.around.early` | ಸುಮಾರು ಬೆಳಗಿನ ಜಾವ {h} ಗಂಟೆಗೆ |
| kn | `say.around.morning` | ಸುಮಾರು ಬೆಳಿಗ್ಗೆ {h} ಗಂಟೆಗೆ |
| kn | `say.around.noon` | ಸುಮಾರು ಮಧ್ಯಾಹ್ನ 12 ಗಂಟೆಗೆ |
| kn | `say.around.afternoon` | ಸುಮಾರು ಮಧ್ಯಾಹ್ನ {h} ಗಂಟೆಗೆ |
| kn | `say.around.evening` | ಸುಮಾರು ಸಂಜೆ {h} ಗಂಟೆಗೆ |
| kn | `say.around.night` | ಸುಮಾರು ರಾತ್ರಿ {h} ಗಂಟೆಗೆ |
| kn | `say.around.midnight` | ಸುಮಾರು ಮಧ್ಯರಾತ್ರಿ 12 ಗಂಟೆಗೆ |
| ar | `say.disclaimer` | هذه توقعات وليست وعداً، لذلك تحقّق من التحذيرات الرسمية أيضاً. سلامتك. |
| ar | `say.replay` | هذه إعادة عرض لطقس يوم {date}. |
| ar | `say.trip_assumed` | افترضتُ رحلة مدتها {hours} ساعات، أخبرني إذا كانت رحلتك مختلفة. |
| ar | `say.safe_summary` | الأمواج حتى {wave} متر، والرياح {wind} والهبّات {gust} كيلومتر في الساعة، كلها أقل من حدود الحذر. |
| ar | `say.reason.unsafe` | {lead} {param}: حتى {value} {unit} {at}، عند حدّ الخطر أو فوقه. |
| ar | `say.reason.caution` | {lead} {param}: حتى {value} {unit} {at}، فوق حدّ الحذر. |
| ar | `say.reason.near` | {lead} {param}: حتى {value} {unit} {at}، قريب من حدّ الحذر. |
| ar | `say.reason.caution_below` | {lead} {param}: تنخفض إلى {value} {unit} {at}، تحت حدّ الحذر. |
| ar | `say.reason.near_below` | {lead} {param}: تنخفض إلى {value} {unit} {at}، قريب من حدّ الحذر. |
| ar | `say.reason.thunderstorm` | قد تحدث عاصفة رعدية {at}. |
| ar | `say.reason.missing` | لا توجد لدينا بيانات {param} {at}، لذلك لا نستطيع القول إنه آمن. |
| ar | `say.reason.beyond_window` | جزء من رحلتك يتجاوز نهاية توقعاتنا. |
| ar | `say.advice.SAFE` | البحر يبدو هادئاً بما يكفي لقارب صغير. |
| ar | `say.advice.CAUTION` | انتبه وأنت في البحر. |
| ar | `say.advice.UNSAFE` | من فضلك لا تخرج بقارب صغير. |
| ar | `say.opener.0` | طيب |
| ar | `say.opener.1` | تمام |
| ar | `say.opener.2` | حسناً |
| ar | `say.verdict_line.SAFE` | {opener}، الخروج {place_from} {day} {time}: يبدو آمناً. |
| ar | `say.verdict_line.CAUTION` | {opener}، الخروج {place_from} {day} {time}: حذر. |
| ar | `say.verdict_line.UNSAFE` | {opener}، الخروج {place_from} {day} {time}: غير آمن. |
| ar | `say.lead.first` | لاحظ |
| ar | `say.lead.middle` | وأيضاً |
| ar | `say.lead.last` | وكذلك |
| ar | `say.param.wave_height` | الأمواج |
| ar | `say.param.wind_speed` | الرياح |
| ar | `say.param.wind_gusts` | الهبّات |
| ar | `say.param.visibility` | مدى الرؤية |
| ar | `say.back` | ستعود {time}. |
| ar | `say.around.early` | حوالي الساعة {h} فجراً |
| ar | `say.around.morning` | حوالي الساعة {h} صباحاً |
| ar | `say.around.noon` | حوالي الساعة 12 ظهراً |
| ar | `say.around.afternoon` | حوالي الساعة {h} بعد الظهر |
| ar | `say.around.evening` | حوالي الساعة {h} مساءً |
| ar | `say.around.night` | حوالي الساعة {h} ليلاً |
| ar | `say.around.midnight` | حوالي منتصف الليل |

### Every harbour at one time, and "when" answers naming the harbour (13 Nov 2026, please check)

New sentences for "which harbours are safe at 1 pm?", and the changed start of the "when is it safe" answer.

| lang | key | text |
|---|---|---|
| kn | `say.safest.day` | {place_from} {day}: |
| kn | `say.list_and` |  ಮತ್ತು  |
| kn | `say.region.intro` | {opener}, {day} {time} {hours} ಗಂಟೆಯ ಪ್ರಯಾಣಕ್ಕೆ ಹೊರಟರೆ: |
| kn | `say.region.none_safe` | ಯಾವ ಬಂದರೂ ಸುರಕ್ಷಿತವಾಗಿ ಕಾಣುತ್ತಿಲ್ಲ. |
| kn | `region.heading` | ಎಲ್ಲಾ ಬಂದರುಗಳು, ಹೊರಡುವುದು {when}, {hours} ಗಂಟೆಯ ಪ್ರಯಾಣ: |
| kn | `region.line` | {verdict}: {places} |
| ar | `say.safest.day` | الخروج {place_from} يوم {day}: |
| ar | `say.list_and` |  و |
| ar | `say.region.intro` | {opener}، للخروج {day} {time} في رحلة مدتها {hours} ساعات: |
| ar | `say.region.none_safe` | لا يبدو أي ميناء آمناً. |
| ar | `region.heading` | كل الموانئ، الانطلاق {when}، رحلة مدتها {hours} ساعات: |
| ar | `region.line` | {verdict}: {places} |

### Remembered harbour line (13 Nov 2026, please check)

Shown in the welcome box when the phone remembers the fisher's usual harbour, with a button to forget it.

| lang | key | text |
|---|---|---|
| kn | `ui.usual` | ಈ ಫೋನಿನಲ್ಲಿ ನೆನಪಿಟ್ಟದ್ದು: {place}{trip}. |
| kn | `ui.usual_trip` | , {hours} ಗಂಟೆಯ ಪ್ರಯಾಣ |
| kn | `ui.forget` | ಮರೆತುಬಿಡಿ |
| ar | `ui.usual` | محفوظ على هذا الهاتف: {place}{trip}. |
| ar | `ui.usual_trip` | ، رحلة مدتها {hours} ساعات |
| ar | `ui.forget` | احذف |
| kn | `say.now` | ಈಗ |
| kn | `ui.region_tap` | ಕಾರಣ ನೋಡಲು ಬಂದರಿನ ಮೇಲೆ ಒತ್ತಿ. |
| ar | `say.now` | الآن |
| ar | `ui.region_tap` | اضغط على ميناء لترى السبب. |
| kn | `say.region.safe_one` | {places} ಸುರಕ್ಷಿತವಾಗಿ ಕಾಣುತ್ತಿದೆ. |
| kn | `say.region.safe_many` | {places} ಸುರಕ್ಷಿತವಾಗಿ ಕಾಣುತ್ತಿವೆ. |
| kn | `say.region.unsafe_one` | {places} ಅಸುರಕ್ಷಿತ. |
| kn | `say.region.unsafe_many` | {places} ಅಸುರಕ್ಷಿತ. |
| kn | `say.region.rest_caution` | ಉಳಿದ ಬಂದರುಗಳಲ್ಲಿ ಎಚ್ಚರಿಕೆ. |
| kn | `say.region.all_safe` | ಎಲ್ಲಾ ಬಂದರುಗಳೂ ಸುರಕ್ಷಿತವಾಗಿ ಕಾಣುತ್ತಿವೆ. |
| kn | `say.region.all_caution` | ಯಾವ ಬಂದರೂ ಸುರಕ್ಷಿತವಾಗಿ ಕಾಣುತ್ತಿಲ್ಲ; ಎಲ್ಲಾ ಕಡೆ ಎಚ್ಚರಿಕೆ. |
| kn | `say.region.all_unsafe` | ಎಲ್ಲಾ ಬಂದರುಗಳೂ ಅಸುರಕ್ಷಿತ. |
| ar | `say.region.safe_one` | {places} يبدو آمناً. |
| ar | `say.region.safe_many` | {places} تبدو آمنة. |
| ar | `say.region.unsafe_one` | {places} غير آمن. |
| ar | `say.region.unsafe_many` | {places} غير آمنة. |
| ar | `say.region.rest_caution` | وباقي الموانئ عليها حذر. |
| ar | `say.region.all_safe` | كل الموانئ تبدو آمنة. |
| ar | `say.region.all_caution` | لا يبدو أي ميناء آمناً، والحذر في كل الموانئ. |
| ar | `say.region.all_unsafe` | كل الموانئ غير آمنة. |

### More kinds of questions (13 Nov 2026, please check)

Weather details (rain, temperature, wind and wave direction, sunrise and sunset), answers about the app itself, and
official warnings. All are fixed sentences; the numbers are filled in by code. These are long: please check that they
are clear when heard, and say if any is too long.

| lang | key | text |
|---|---|---|
| kn | `param.air_temperature` | ಗಾಳಿ °C |
| kn | `param.rain` | ಮಳೆ ಮಿಮೀ |
| kn | `param.sea_temperature` | ಸಮುದ್ರ °C |
| kn | `card.sun` | ಸೂರ್ಯೋದಯ {rise}, ಸೂರ್ಯಾಸ್ತ {set} (ಸ್ಥಳೀಯ ಸಮಯ). |
| kn | `say.details.intro` | {opener}, {place_from} {day} {time} ಹೊರಡುವ ಪ್ರಯಾಣಕ್ಕೆ: |
| kn | `say.details.air_range` | ಗಾಳಿಯ ತಾಪಮಾನ {min} ರಿಂದ {max} ಡಿಗ್ರಿ. |
| kn | `say.details.air_one` | ಗಾಳಿಯ ತಾಪಮಾನ ಸುಮಾರು {t} ಡಿಗ್ರಿ. |
| kn | `say.details.sea` | ಸಮುದ್ರದ ನೀರು ಸುಮಾರು {t} ಡಿಗ್ರಿ. |
| kn | `say.details.no_rain` | ಮಳೆಯ ನಿರೀಕ್ಷೆ ಇಲ್ಲ. |
| kn | `say.details.rain` | ಪ್ರತಿ ಗಂಟೆಗೆ {mm} ಮಿಲಿಮೀಟರ್ ವರೆಗೆ ಮಳೆ, {at}. |
| kn | `say.details.wind_dir` | ಗಾಳಿ {dir} ದಿಕ್ಕಿನಿಂದ ಬೀಸುತ್ತದೆ. |
| kn | `say.details.waves` | ಅಲೆಗಳು {dir} ದಿಕ್ಕಿನಿಂದ, ಸುಮಾರು {s} ಸೆಕೆಂಡಿಗೊಮ್ಮೆ ಬರುತ್ತವೆ. |
| kn | `say.details.sun` | ಸೂರ್ಯೋದಯ {rise}, ಸೂರ್ಯಾಸ್ತ {set}. |
| kn | `say.details.none` | ಆ ಸಮಯಕ್ಕೆ ಈ ವಿವರಗಳು ನನ್ನ ಬಳಿ ಇಲ್ಲ. |
| kn | `say.details.verdict.SAFE` | ಆ ಪ್ರಯಾಣಕ್ಕೆ ಸುರಕ್ಷತಾ ಪರಿಶೀಲನೆ: ಸುರಕ್ಷಿತವಾಗಿ ಕಾಣುತ್ತಿದೆ. |
| kn | `say.details.verdict.CAUTION` | ಆ ಪ್ರಯಾಣಕ್ಕೆ ಸುರಕ್ಷತಾ ಪರಿಶೀಲನೆ: ಎಚ್ಚರಿಕೆ. |
| kn | `say.details.verdict.UNSAFE` | ಆ ಪ್ರಯಾಣಕ್ಕೆ ಸುರಕ್ಷತಾ ಪರಿಶೀಲನೆ: ಅಸುರಕ್ಷಿತ. |
| kn | `faq.verdicts` | ಸುರಕ್ಷಿತ ಎಂದರೆ ನಿಮ್ಮ ಪ್ರಯಾಣದ ಪ್ರತಿ ಗಂಟೆಯೂ ಎಲ್ಲಾ ಎಚ್ಚರಿಕೆಯ ಮಿತಿಗಳಿಗಿಂತ ಕಡಿಮೆ ಇದೆ. ಎಚ್ಚರಿಕೆ ಎಂದರೆ ಯಾವುದಾದರೂ ಒಂದು ಎಚ್ಚರಿಕೆಯ ಮಿತಿಯನ್ನು ದಾಟಿದೆ, ಅದಕ್ಕೆ ಹತ್ತಿರವಿದೆ, ಅಥವಾ ಮಾಹಿತಿ ಇಲ್ಲ, ಆದ್ದರಿಂದ ಜಾಗ್ರತೆ ವಹಿಸಿ. ಅಸುರಕ್ಷಿತ ಎಂದರೆ ಅಲೆಗಳು, ಗಾಳಿ ಅಥವಾ ಹಠಾತ್ ಬಿರುಗಾಳಿ ಅಸುರಕ್ಷಿತ ಮಿತಿಯನ್ನು ತಲುಪಿವೆ: ಸಣ್ಣ ದೋಣಿಯಲ್ಲಿ ಹೋಗಬೇಡಿ. |
| kn | `faq.how_decided` | ನಿಮ್ಮ ಬಂದರಿಗೆ ಹತ್ತಿರದ ಸಮುದ್ರ ಬಿಂದುವಿನಲ್ಲಿ, ಪ್ರಯಾಣದ ಪ್ರತಿ ಗಂಟೆಗೂ ಅಲೆಗಳು, ಗಾಳಿ, ಹಠಾತ್ ಬಿರುಗಾಳಿ, ಗುಡುಗು ಮತ್ತು ಗೋಚರತೆಯನ್ನು ಪರಿಶೀಲಿಸುತ್ತೇನೆ. ಅಲೆಗಳು {wave_c} ಮೀಟರ್, ಗಾಳಿ {wind_c} ಅಥವಾ ಹಠಾತ್ ಬಿರುಗಾಳಿ {gust_c} ಕಿಲೋಮೀಟರ್ ಪ್ರತಿ ಗಂಟೆಗೆ ತಲುಪಿದರೆ, ಗೋಚರತೆ {vis_c} ಮೀಟರ್ ಅಥವಾ ಕಡಿಮೆಯಾದರೆ, ಅಥವಾ ಗುಡುಗು ಇದ್ದರೆ ಎಚ್ಚರಿಕೆ. ಅಲೆಗಳು {wave_u} ಮೀಟರ್, ಗಾಳಿ {wind_u} ಅಥವಾ ಹಠಾತ್ ಬಿರುಗಾಳಿ {gust_u} ಕಿಲೋಮೀಟರ್ ಪ್ರತಿ ಗಂಟೆಗೆ ತಲುಪಿದರೆ ಅಸುರಕ್ಷಿತ. ಅತ್ಯಂತ ಕೆಟ್ಟ ಗಂಟೆಯೇ ನಿರ್ಧರಿಸುತ್ತದೆ. |
| kn | `faq.sources` | ಪ್ರತಿ ಮಿತಿಯೂ ಪ್ರಕಟಿತ ಮೂಲದಿಂದ ಬಂದಿದೆ: ವಿಶ್ವ ಹವಾಮಾನ ಸಂಸ್ಥೆಯ ಸಮುದ್ರ ಕೈಪಿಡಿಗಳು, ಸಣ್ಣ ಮೀನುಗಾರಿಕಾ ದೋಣಿಗಳಿಗೆ FAO ಸುರಕ್ಷತಾ ನಿಯಮಗಳು, ಮತ್ತು ಭಾರತೀಯ ಹವಾಮಾನ ಇಲಾಖೆಯ ಮೀನುಗಾರರ ಎಚ್ಚರಿಕೆಗಳು. ಪ್ರತಿಯೊಂದನ್ನೂ ನೋಡಲು '{how}' ಒತ್ತಿ. |
| kn | `faq.near_line` | ಯಾವುದಾದರೂ ಮೌಲ್ಯ ಎಚ್ಚರಿಕೆಯ ಮಿತಿಗೆ ಶೇಕಡಾ {pct} ರೊಳಗೆ ಇದ್ದರೆ, ಮುನ್ಸೂಚನೆ ಸ್ವಲ್ಪ ತಪ್ಪಬಹುದಾದ್ದರಿಂದ ಸುರಕ್ಷಿತ ಎನ್ನದೆ ಎಚ್ಚರಿಕೆ ಎನ್ನುತ್ತೇನೆ. ಈ ನಿಯಮ ನಮ್ಮದು, ಯಾವುದೇ ಮೂಲದಿಂದ ಬಂದದ್ದಲ್ಲ. |
| kn | `faq.boats` | ಈ ಮಿತಿಗಳು 10 ಮೀಟರ್‌ಗಿಂತ ಚಿಕ್ಕ ತೆರೆದ ದೋಣಿಗಳಿಗೆ. ದೊಡ್ಡ ದೋಣಿಗಳು ಹೆಚ್ಚು ತಡೆದುಕೊಳ್ಳಬಲ್ಲವು, ಆದರೆ ಅವುಗಳಿಗೆ ನಾನು ಪರಿಶೀಲಿಸುವುದಿಲ್ಲ. |
| kn | `faq.accuracy` | ಮುನ್ಸೂಚನೆ ಉತ್ತಮ ಅಂದಾಜು ಮಾತ್ರ, ಖಾತರಿ ಅಲ್ಲ; ಮುಂದೆ ಹೋದಂತೆ ಅದು ಕಡಿಮೆ ಖಚಿತವಾಗುತ್ತದೆ. ನಾನು ಮುಂದಿನ {window} ಗಂಟೆಗಳನ್ನು ಮಾತ್ರ ನೋಡುತ್ತೇನೆ, ಮತ್ತು ಮಾಹಿತಿ {stale} ಗಂಟೆಗಿಂತ ಹಳೆಯದಾದರೆ ಎಚ್ಚರಿಕೆ ಎನ್ನುತ್ತೇನೆ. ಅಧಿಕೃತ ಎಚ್ಚರಿಕೆಗಳನ್ನೂ ಯಾವಾಗಲೂ ನೋಡಿ. |
| kn | `faq.data_source` | ಹವಾಮಾನ ಮಾಹಿತಿ Open-Meteo ಇಂದ ಬರುತ್ತದೆ: ಅಲೆಗಳು {marine} ಮಾದರಿಯಿಂದ, ಗಾಳಿ {weather} ಮಾದರಿಯಿಂದ. ಈಗಿನ ಮಾಹಿತಿಯನ್ನು ಪ್ರತಿ {cache} ನಿಮಿಷಕ್ಕೊಮ್ಮೆ ಹೊಸದಾಗಿ ಪಡೆಯಲಾಗುತ್ತದೆ. |
| kn | `faq.replay` | ಮರುಪ್ರದರ್ಶನ ಹಿಂದಿನ ಒಂದು ದಿನ ದಾಖಲಾದ ಹವಾಮಾನವನ್ನು ಇಂದಿನಂತೆ ತೋರಿಸುತ್ತದೆ, ಕೆಟ್ಟ ದಿನದಲ್ಲಿ ಆ್ಯಪ್ ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ ಎಂದು ನೋಡಲು. ಇದು ಇಂದಿನ ಮುನ್ಸೂಚನೆ ಅಲ್ಲ. |
| kn | `faq.missing_data` | ನಿಮ್ಮ ಪ್ರಯಾಣದ ಯಾವುದೇ ಗಂಟೆಗೆ ಮಾಹಿತಿ ಇಲ್ಲದಿದ್ದರೆ, ನಾನು ಎಚ್ಚರಿಕೆ ಎನ್ನುತ್ತೇನೆ, ಎಂದಿಗೂ ಸುರಕ್ಷಿತ ಎನ್ನುವುದಿಲ್ಲ. |
| kn | `faq.memory` | ಈ ಫೋನ್ ನಿಮ್ಮ ಸಾಮಾನ್ಯ ಬಂದರು ಮತ್ತು ಪ್ರಯಾಣದ ಅವಧಿಯನ್ನು ಮಾತ್ರ ನೆನಪಿಡುತ್ತದೆ. ಸರ್ವರ್ ಯಾವುದೇ ಸಂಭಾಷಣೆಯನ್ನು ಉಳಿಸುವುದಿಲ್ಲ, ಬೇರೆ ಏನೂ ಸಂಗ್ರಹವಾಗುವುದಿಲ್ಲ. |
| kn | `faq.limits` | ನಾನು ಈ ಬಂದರುಗಳಿಂದ ಸಣ್ಣ ದೋಣಿಗಳಿಗೆ ಮುಂದಿನ {window} ಗಂಟೆಗಳ ಸಮುದ್ರ ಸುರಕ್ಷತೆಯನ್ನು ಪರಿಶೀಲಿಸುತ್ತೇನೆ: ಅಲೆಗಳು, ಗಾಳಿ, ಹಠಾತ್ ಬಿರುಗಾಳಿ, ಗುಡುಗು ಮತ್ತು ಗೋಚರತೆ, ಜೊತೆಗೆ ಮಳೆ, ತಾಪಮಾನ, ಸೂರ್ಯೋದಯ ಮತ್ತು ಸೂರ್ಯಾಸ್ತ. ಉಬ್ಬರವಿಳಿತ, ಸಮುದ್ರದ ಪ್ರವಾಹಗಳು ಅಥವಾ ಮೀನು ಎಲ್ಲಿದೆ ಎಂಬುದನ್ನು ಪರಿಶೀಲಿಸಲು ನನಗೆ ಆಗುವುದಿಲ್ಲ. |
| kn | `say.official.warnings` | ಅಧಿಕೃತ ಎಚ್ಚರಿಕೆಗಳಿಗಾಗಿ {names} ನೋಡಿ. ಲಿಂಕ್‌ಗಳು ಪರದೆಯ ಮೇಲಿವೆ. |
| kn | `say.official.contacts` | ಸಮುದ್ರದಲ್ಲಿ ತುರ್ತು ಪರಿಸ್ಥಿತಿಯಲ್ಲಿ ಕರೆ ಮಾಡಿ: {contacts}. |
| kn | `say.official.contact` | {name}, {number} |
| kn | `say.official.no_contacts` | ತುರ್ತು ಪರಿಸ್ಥಿತಿಯಲ್ಲಿ ನಿಮ್ಮ ಸ್ಥಳೀಯ ತುರ್ತು ಸಂಖ್ಯೆಗೆ ಕರೆ ಮಾಡಿ. |
| ar | `param.air_temperature` | حرارة الجو °م |
| ar | `param.rain` | مطر ملم |
| ar | `param.sea_temperature` | حرارة البحر °م |
| ar | `card.sun` | الشروق {rise}، الغروب {set} (بالتوقيت المحلي). |
| ar | `say.details.intro` | {opener}، لرحلة {place_from} {day} {time}: |
| ar | `say.details.air_range` | درجة حرارة الجو من {min} إلى {max} درجة. |
| ar | `say.details.air_one` | درجة حرارة الجو حوالي {t} درجة. |
| ar | `say.details.sea` | حرارة البحر حوالي {t} درجة. |
| ar | `say.details.no_rain` | لا يُتوقع مطر. |
| ar | `say.details.rain` | مطر حتى {mm} ملم في الساعة، {at}. |
| ar | `say.details.wind_dir` | الرياح تهب من {dir}. |
| ar | `say.details.waves` | الأمواج تأتي من {dir}، كل {s} ثوانٍ تقريباً. |
| ar | `say.details.sun` | الشروق {rise} والغروب {set}. |
| ar | `say.details.none` | لا تتوفر لدي هذه التفاصيل لذلك الوقت. |
| ar | `say.details.verdict.SAFE` | فحص السلامة لهذه الرحلة: يبدو آمناً. |
| ar | `say.details.verdict.CAUTION` | فحص السلامة لهذه الرحلة: حذر. |
| ar | `say.details.verdict.UNSAFE` | فحص السلامة لهذه الرحلة: غير آمن. |
| ar | `faq.verdicts` | آمن يعني أن كل ساعة من رحلتك تحت كل حدود الحذر. حذر يعني أن شيئاً ما فوق حدّ الحذر أو قريب منه أو بدون بيانات، فانتبه. غير آمن يعني أن الأمواج أو الرياح أو الهبّات بلغت حدّ الخطر: لا تخرج بقارب صغير. |
| ar | `faq.how_decided` | لكل ساعة من رحلتك، عند أقرب نقطة بحرية لمينائك، أفحص الأمواج والرياح والهبّات والعواصف الرعدية ومدى الرؤية. يكون حذراً إذا بلغت الأمواج {wave_c} متر، أو الرياح {wind_c} أو الهبّات {gust_c} كيلومتر في الساعة، أو كان مدى الرؤية {vis_c} متر أو أقل، أو كانت هناك عاصفة رعدية. ويكون غير آمن إذا بلغت الأمواج {wave_u} متر، أو الرياح {wind_u} أو الهبّات {gust_u} كيلومتر في الساعة. أسوأ ساعة هي التي تقرر. |
| ar | `faq.sources` | كل حدّ مأخوذ من مصدر منشور: أدلة المنظمة العالمية للأرصاد الجوية للبحر، وقواعد السلامة من منظمة الفاو لقوارب الصيد الصغيرة، وتحذيرات الصيادين من دائرة الأرصاد الجوية الهندية. اضغط على '{how}' لترى كل مصدر. |
| ar | `faq.near_line` | إذا كانت القيمة ضمن {pct} بالمئة من حدّ الحذر أقول حذر بدلاً من آمن، لأن التوقعات قد تخطئ قليلاً. هذه قاعدتنا نحن، وليست من مصدر. |
| ar | `faq.boats` | هذه الحدود للقوارب الصغيرة المكشوفة التي يقل طولها عن 10 أمتار. القارب الأكبر يتحمل أكثر، لكنني لا أفحص للقوارب الأكبر. |
| ar | `faq.accuracy` | التوقعات أفضل تقدير وليست ضماناً، وتقل دقتها كلما ابتعد الوقت. أنظر فقط إلى الساعات {window} القادمة، وإذا كانت البيانات أقدم من {stale} ساعات أقول حذر. تحقّق دائماً من التحذيرات الرسمية أيضاً. |
| ar | `faq.data_source` | بيانات الطقس من Open-Meteo: الأمواج من نموذج {marine} والرياح من نموذج {weather}. تُحدَّث البيانات الحالية كل {cache} دقيقة. |
| ar | `faq.replay` | إعادة العرض تُظهر طقساً سُجّل في يوم سابق كأنه اليوم، لترى كيف يتعامل التطبيق مع يوم صعب. إنها ليست توقعات اليوم. |
| ar | `faq.missing_data` | إذا لم تتوفر بيانات لأي ساعة من رحلتك أقول حذر، ولا أقول آمن أبداً. |
| ar | `faq.memory` | هذا الهاتف يحفظ فقط مينائك المعتاد ومدة رحلتك. الخادم لا يحفظ أي محادثات، ولا يُخزَّن أي شيء آخر. |
| ar | `faq.limits` | أفحص سلامة البحر للقوارب الصغيرة من هذه الموانئ خلال الساعات {window} القادمة: الأمواج والرياح والهبّات والعواصف الرعدية ومدى الرؤية، إضافة إلى المطر ودرجة الحرارة والشروق والغروب. لا أستطيع فحص المد والجزر أو التيارات أو أماكن السمك. |
| ar | `say.official.warnings` | للتحذيرات الرسمية راجع {names}. الروابط على الشاشة. |
| ar | `say.official.contacts` | في حالة طوارئ في البحر اتصل بـ: {contacts}. |
| ar | `say.official.contact` | {name}، {number} |
| ar | `say.official.no_contacts` | في حالة الطوارئ اتصل برقم الطوارئ المحلي. |
| kn | `contact.coast_guard_in` | ಭಾರತೀಯ ಕರಾವಳಿ ಕಾವಲು ಪಡೆ |
| kn | `contact.coast_guard_ae` | ಯುಎಇ ಕರಾವಳಿ ಕಾವಲು ಪಡೆ |
| ar | `contact.coast_guard_in` | خفر السواحل الهندي |
| ar | `contact.coast_guard_ae` | خفر السواحل |
