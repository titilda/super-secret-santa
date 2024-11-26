# 🎅 Super Secret Santa 🎁

**Super Secret Santa** is a Discord bot designed to bring the joy of Secret Santa to your server! Organize campaigns, manage participants, and exchange anonymous gifts—all through easy-to-use commands and buttons.

[![Add to Discord](https://img.shields.io/badge/Add%20to%20Discord-7289DA?logo=discord&logoColor=white)](https://discord.com/oauth2/authorize?client_id=1308427430385418270&scope=applications.commands&permissions=1143915147611200) [![License](https://img.shields.io/github/license/titilda/super-secret-santa)](https://github.com/titilda/super-secret-santa/blob/main/LICENSE) [![Python](https://img.shields.io/badge/Python-3.15%2B-blue?logo=python)](https://www.python.org/downloads/) [![Docker](https://img.shields.io/badge/Docker%20Image-blue?logo=docker)](https://ghcr.io/titilda/super-secret-santa)

---

## ✨ Features
- **Create Campaigns**: Organize Secret Santa campaigns with `/santa create`.
- **Join or Leave**: Participants can join or leave a campaign with intuitive buttons.
- **Start the Fun**: The organizer starts the gift exchange, assigning giftees randomly.
- **Send Messages**: Anonymous message exchange with `/santa message`.
- **Secure & Persistent**: Campaigns are stored securely in a PostgreSQL database.

---

## 🛠 Commands
### `/santa create <name>`
Create a new Secret Santa campaign in your server.

### `/santa delete`
Delete a campaign. Only the organizer can delete a campaign.

### `/santa message <message>`
Send a message anonymously to your assigned giftee.

---

## 📦 Setup
1. **Dependencies**: you need [Poetry](https://python-poetry.org/) to manage packages. Run `poetry install` to install the dependencies.
2. **Database**: the bot uses PostgreSQL for persistence. Ensure your database is accessible and apply the schema in `schema.sql`.
3. **Config**: specify your database and Discord credentials via `config.ini` as per `config.ini.example`.
4. **Launch the bot**: run `poetry run python super_secret_santa` to start the bot.
5. **Add to Discord**: invite the bot to your server using the link that appears in the console.