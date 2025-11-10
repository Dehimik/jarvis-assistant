# About Jarvis Assistant

Jarvis Assistant is a desktop voice assistant designed to simplify interaction with your computer. Its primary goal is to give you the ability to manage the launching and closing of applications, websites, and scripts using your voice.

## Interface Overview

All of the application's functionality is conveniently divided into several key pages:

### 1. Dashboard

This is your main screen. Here, you can activate or deactivate the assistant. The dashboard displays the current status: whether Jarvis is listening, processing a command, or in standby mode.

### 2. Settings

Here you can configure the assistant for your specific hardware and needs:

* **Microphone Selection:** Specify which input device will be used for voice recognition.
* **Speaker Selection:** Specify the device through which the assistant will voice its responses.
* **Localization & OpenAI API:** These fields are currently experimental and reserved for future updates that will expand functionality.

### 3. Logs

This is a key page for monitoring and diagnostics. Two things happen here:

* **Real-time Logs:** You can see a stream of messages about what the assistant is doing (e.g., "phrase recognized," "command not found," "launching application...").
* **File Access:** There is a button to open the log file in your computer's default text editor.
* **Database:** All logs are also duplicated to a PostgreSQL database into two separate tables: one table contains every single system message, while the other holds only the history of executed commands and recognition errors.

### 4. Intents

The heart of your assistant. This is the built-in editor for command (.yaml) files. This is where you "teach" Jarvis which applications and websites it should open or close. You can add new programs, specify paths to them, and assign synonyms (e.g., so that "open browser" and "launch chrome" do the same thing).

### 5. About

The page you are currently on, which describes the program's features.

---

## How to Create Commands (Intents)

All commands are stored in .yaml files. You can edit them on the "Intents" page. The file structure is very simple and based on a template.

**Here is the basic template (from test.yaml):**

```yaml
intents:
  app.open:
    patterns:
      - "open {app:app_name}"
      - "open1 {app:app_name}"
    slots:
      app:
        type: app_name
        synonyms:
          app_name: ["synonym1", "synonym2"]
          https://site.com: ["synonym1", "synonym2"]
  app.close:
    patterns:
      - "close {app:app_name}"
      - "close1 {app:app_name}"
    slots:
      app:
        type: app_name
        synonyms:
          app_name: ["synonym1", "synonym2"]
```
### Structure Explained:

* **intents:** — Must have.
* **app.open: / app.close:** — Unique name of your intent. You can call it whatever you want (e.g., script.run or site.open) but you have to write a plugin for it.
* **patterns:** — Phrases list, that will recognize assistant.
* **{app:app_name}** — Changable part, called a "slot." It consists of two parts:
    * app — It's **name** of slot.
    * app_name — It's **type** of slot..
* **slots:** — Here we describe what our slots mean.
    * app: — The name must match the slot name in patterns.
    * type: — The type must match the slot type in patterns.
    * **synonyms:** — The most important part. This is a dictionary where:
        * **Key** (e.g., app_name or https://site.com) — This is the **real path to the program, website URL, or command** that will be executed.
        * **Value** (e.g., ["synonym1", "synonym2"]) — This is a list of words that the user can say to activate this key.

### Real-life Example:

If you want open some program and site or close some program:
```yaml
intents:
  app.open:
    patterns:
      - "open {app:my_apps}"
      - "відкрий {app:my_apps}"
    slots:
      app:
        type: my_apps
        synonyms:
          discord: ["discord", "діскордік"]
          https://youtube.com: ["youtube", "ютуб"]
  app.close:
    patterns:
      - "close {app:my_apps}"
      - "закрий {app:my_apps}"
    slots:
      app:
        type: my_apps
        synonyms:
          discord: ["discord", "діскордік"]
          chromium: ["chrome", "chromium", "хром"]
```

Now, if you tell "launch chrome" or "open github," Jarvis will execute commnand.

---

## Future Updates

There are current plans to add a full-fledged graphical editor for creating and managing custom plugins. This will allow non-programmers to easily extend the assistant's functionality by adding new types of voice recognition or response sources.

---

## Developer

This project was developed by **Dehimik**.

You can find more of my projects on my GitHub:
[**https://github.com/Dehimik**](https://github.com/Dehimik)