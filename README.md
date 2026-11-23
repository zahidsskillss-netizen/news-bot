# د خبرونو روباټ — Ghora Graphics

له خبري سایتونو تازه خبرونه هر ۳ ساعته په اتومات ډول ټلګرام چینل ته لېږي. په GitHub Actions باندې وړیا چلېږي.

## د جوړولو ګامونه
1. **روباټ:** په ټلګرام کې @BotFather ته `/newbot` ولیکئ. هغه Token چې درکول کېږي، وساتئ.
2. **چینل:** یو Public چینل جوړ کړئ (مثلاً `@GhoraNews`). روباټ پکې Admin کړئ او د Post Messages اجازه ورکړئ.
3. **GitHub:** یو نوی repo جوړ کړئ او دا فایلونه پکې واچوئ (`.github/workflows/news.yml` هم ورسره).
4. **Secrets:** په repo کې Settings ← Secrets and variables ← Actions ← New repository secret ته لاړ شئ او دا ورزیات کړئ:
   - `TELEGRAM_BOT_TOKEN` — د BotFather Token
   - `TELEGRAM_CHANNEL` — د چینل یوزرنېم، لکه `@GhoraNews`
   - `CHANNEL_SIGNATURE` (اختیاري) — هغه متن چې د هر پوسټ په پای کې راځي
   - `GEMINI_API_KEY` (اختیاري) — که AI خبرونه لنډ کړي یا انګلیسي خبرونه پښتو ته وژباړي
5. **ازموینه:** Actions ← News Bot ← Run workflow. په لاګ کې به ووینئ چې کوم خبرونه خپاره شول.

## بدلونونه
- **سرچینې:** `feeds.txt`
- **څو ځله خپرېږي:** د `news.yml` په `cron` کې. د بېلګې په توګه `0 */3 * * *` یعني هر ۳ ساعته.
- **په هر ځل څو خبرونه:** `MAX_PER_RUN`
