#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QQmlContext>
#include <QCommandLineParser>
#include <QSet>

QVariantMap loadJsonConfig(const QString &filePath) {
    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        qWarning() << "Failed to open config file:" << filePath;
        return {};
    }

    QByteArray jsonData = file.readAll();
    file.close();

    QJsonDocument doc = QJsonDocument::fromJson(jsonData);
    if (!doc.isObject()) {
        qWarning() << "Invalid JSON format";
        return {};
    }

    return doc.object().toVariantMap();
}

void overrideConfigWithArgs(QVariantMap &config, const QGuiApplication &app)
{
    QCommandLineParser parser;
    parser.setApplicationDescription("Application with JSON config and arguments");
    parser.addHelpOption();

    QCommandLineOption bakeLightmapsOption("bake-lightmaps", "Triggers lightmap baking");
    parser.addOption(bakeLightmapsOption);

    for (auto [key, _] : config.asKeyValueRange()) {
        parser.addOption(QCommandLineOption(key, QString("Override %1").arg(key), "value"));
    }

    parser.process(app);

    for (const QString &arg : parser.optionNames()) {
        if (!config.contains(arg) && arg != "bake-lightmaps") {
            qFatal("Invalid command-line argument: %s (not present in JSON)", qUtf8Printable(arg));
        }

        if (config[arg].typeId() == QMetaType::Bool) {
            QString value = parser.value(arg).trimmed().toLower();
            if (value == "true" || value == "1") {
                config[arg] = true;
            } else if (value == "false" || value == "0") {
                config[arg] = false;
            }
        } else {
            config[arg] = parser.value(arg);
        }
    }

    // Apply model-specific overrides
    if (config.contains("model")) {
        QString modelName = config["model"].toString();
        if (config.contains(modelName)) {
            QVariantMap modelOverrides = config[modelName].toMap();
            for (auto [key, value] : modelOverrides.asKeyValueRange()) {
                config[key] = value;
            }
        }
    }
}

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QQmlApplicationEngine engine;

    QVariantMap config = loadJsonConfig(":/config.json");

    overrideConfigWithArgs(config, app);

    engine.rootContext()->setContextProperty("appConfig", config);

    const QUrl url(QStringLiteral("qrc:/Main.qml"));

    QObject::connect(&engine, &QQmlApplicationEngine::objectCreated,
                     &app, [url](QObject *obj, const QUrl &objUrl) {
                         if (!obj && url == objUrl)
                             QCoreApplication::exit(-1);
                     }, Qt::QueuedConnection);
    engine.load(url);

    return app.exec();
}
