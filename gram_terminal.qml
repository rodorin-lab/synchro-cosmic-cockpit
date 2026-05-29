import QtQuick
import QtQuick.Controls

Window {
    id: window
    width: 1100
    height: 750
    visible: true
    title: "🛸 グラムちゃん・コズミック・ターミナル v0.2 🛸"
    color: "#030206"

    CosmicBackground {
        anchors.fill: parent
    }

    Rectangle {
        id: statusBar
        anchors.top: parent.top
        width: parent.width
        height: 45
        color: "#0a0a1a"
        border.color: "#00f0ff"
        border.width: 2

        Row {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 25

            Text {
                id: cpuText
                text: "🔥 CPU: --"
                color: "#ff007f"
                font.family: "monospace"
                font.pixelSize: 14
                font.bold: true
            }
            Text {
                id: memText
                text: "🌊 MEM: --"
                color: "#00f0ff"
                font.family: "monospace"
                font.pixelSize: 14
                font.bold: true
            }
            Text {
                id: swapText
                text: "🌌 SWAP: --"
                color: "#ffd700"
                font.family: "monospace"
                font.pixelSize: 14
                font.bold: true
            }
            Text {
                id: diskText
                text: "💾 DISK: --"
                color: "#00ff88"
                font.family: "monospace"
                font.pixelSize: 14
                font.bold: true
            }
        }
    }

    Rectangle {
        id: chatArea
        anchors.top: statusBar.bottom
        anchors.bottom: inputArea.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 12
        color: "#050510"
        border.color: "#ff007f"
        border.width: 2
        radius: 8

        ListView {
            id: chatList
            anchors.fill: parent
            anchors.margins: 10
            clip: true
            spacing: 8
            model: ListModel { id: chatModel }

            delegate: Rectangle {
                width: chatList.width
                height: msgText.height + 16
                color: agent.indexOf("グラム") >= 0 ? "rgba(255, 0, 127, 0.15)" : (agent.indexOf("司令官") >= 0 ? "rgba(255, 215, 0, 0.12)" : "rgba(0, 240, 255, 0.1)")
                radius: 6
                border.color: agent.indexOf("グラム") >= 0 ? "#ff007f" : (agent.indexOf("司令官") >= 0 ? "#ffd700" : "#00f0ff")
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 4

                    Text {
                        text: agent
                        color: agent.indexOf("グラム") >= 0 ? "#ff007f" : (agent.indexOf("司令官") >= 0 ? "#ffd700" : "#00f0ff")
                        font.pixelSize: 11
                        font.bold: true
                        font.family: "monospace"
                    }
                    Text {
                        id: msgText
                        text: message
                        color: "#ffffff"
                        font.pixelSize: 13
                        font.family: "monospace"
                        width: parent.width
                        wrapMode: Text.Wrap
                    }
                }
            }

            onCountChanged: chatList.positionViewAtEnd()
        }
    }

    Rectangle {
        id: inputArea
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 55
        color: "#0a0a1a"
        border.color: "#00f0ff"
        border.width: 2

        TextField {
            id: chatInput
            anchors.fill: parent
            anchors.margins: 8
            color: "#ffffff"
            font.pixelSize: 14
            font.family: "monospace"
            placeholderText: "お兄ちゃん、ここにメッセージを入力してね... 🛸"
            placeholderTextColor: "rgba(255, 255, 255, 0.3)"
            background: Rectangle {
                color: "#050510"
                border.color: "#00f0ff"
                border.width: 1
                radius: 6
            }

            onAccepted: {
                if (text.trim().length > 0) {
                    chatModel.append({agent: "👑 ロドリン司令官", message: text});
                    gramBridge.send_chat("ロドリン司令官", text);
                    text = "";
                }
            }
        }
    }

    GramChan {
        id: miniGram
        anchors.right: parent.right
        anchors.bottom: inputArea.top
        anchors.rightMargin: 20
        anchors.bottomMargin: 15
        mood: "normal"
    }

    Timer {
        interval: 3000
        running: true
        repeat: true
        onTriggered: {
            var status = JSON.parse(gramBridge.get_system_status());
            if (status.status === "success") {
                var mem = status.memory || {};
                var swap = status.swap || {};
                var disk = status.disk || {};
                var load = status.loadavg || ["--", "--", "--"];

                var memPct = mem.total > 0 ? Math.round((mem.total - mem.available) / mem.total * 100) : 0;
                var swapPct = swap.total > 0 ? Math.round((1 - swap.free / swap.total) * 100) : 0;
                var diskPct = disk.total > 0 ? Math.round(disk.used / disk.total * 100) : 0;

                cpuText.text = "🔥 CPU: " + load[0];
                memText.text = "🌊 MEM: " + memPct + "%";
                swapText.text = "🌌 SWAP: " + swapPct + "%";
                diskText.text = "💾 DISK: " + diskPct + "%";
            }
        }
    }

    Connections {
        target: gramBridge
        function onMessageReceived(agent, message) {
            chatModel.append({agent: agent, message: message});
        }
        function onCommandResult(result) {
            chatModel.append({agent: "⚡ システム", message: result});
        }
    }

    Component.onCompleted: {
        chatModel.append({agent: "🛸💙 グラムちゃん", message: "お兄ちゃん！コズミック・QML・ターミナル、起動完了だよ！何でも話しかけてね！✨"});
    }
}
