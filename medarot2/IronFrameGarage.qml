import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    width: 1280
    height: 720
    color: "#1A1A2E"

    property var parts: [
        { name: "シールドヘッド", slot: "HEAD", rank: "B", atk: 0, def: 30, spd: 0, en: 0, weight: 12, color: "#3498db" },
        { name: "スナイパーアイ", slot: "HEAD", rank: "A", atk: 10, def: 10, spd: 5, en: 15, weight: 8, color: "#f1c40f" },
        { name: "重装コア", slot: "CORE", rank: "A", atk: 0, def: 50, spd: -10, en: 20, weight: 40, color: "#f1c40f" },
        { name: "高機動コア", slot: "CORE", rank: "B", atk: 0, def: 20, spd: 15, en: 25, weight: 18, color: "#3498db" },
        { name: "バルカン", slot: "R-ARM", rank: "C", atk: 25, def: 0, spd: 0, en: 5, weight: 10, color: "#95a5a6" },
        { name: "ビームセイバー", slot: "R-ARM", rank: "A", atk: 55, def: 0, spd: 10, en: 20, weight: 14, color: "#f1c40f" },
        { name: "シールドアーム", slot: "L-ARM", rank: "B", atk: 0, def: 35, spd: -5, en: 0, weight: 15, color: "#3498db" },
        { name: "グラップラー", slot: "L-ARM", rank: "A", atk: 40, def: 15, spd: 5, en: 10, weight: 16, color: "#f1c40f" },
        { name: "キャタピラ脚", slot: "LEGS", rank: "B", atk: 0, def: 25, spd: -5, en: 0, weight: 30, color: "#3498db" },
        { name: "ジェット脚", slot: "LEGS", rank: "A", atk: 0, def: 15, spd: 25, en: 15, weight: 12, color: "#f1c40f" },
        { name: "ステルスブースター", slot: "BOOSTER", rank: "S", atk: 0, def: 0, spd: 20, en: 30, weight: 8, color: "#e74c3c" },
        { name: "タクティクスOS", slot: "BOOSTER", rank: "A", atk: 5, def: 5, spd: 10, en: 25, weight: 6, color: "#f1c40f" }
    ]

    property var equipped: ({
        "HEAD": null,
        "CORE": null,
        "R-ARM": null,
        "L-ARM": null,
        "LEGS": null,
        "BOOSTER": null
    })

    function equip(part) {
        var e = {};
        for (var k in equipped) e[k] = equipped[k];
        e[part.slot] = part;
        equipped = e;
    }

    function totalStat(key) {
        var sum = 0;
        for (var slot in equipped) {
            if (equipped[slot]) sum += equipped[slot][key];
        }
        return sum;
    }

    function totalWeight() { return totalStat("weight"); }

    function loadLimit() {
        var legs = equipped["LEGS"];
        return legs ? legs.def * 2 + 20 : 20;
    }

    function synergy() {
        var count = 0;
        for (var slot in equipped) if (equipped[slot]) count++;
        if (count >= 4) return "SPEED FRAME (4部位装備中)";
        return "なし";
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        Rectangle {
            Layout.fillWidth: true
            height: 60
            color: "#16213E"
            radius: 8
            border.color: "#533483"
            border.width: 2

            Text {
                anchors.centerIn: parent
                text: "🔮 IRON FRAME — ガレージ"
                color: "#E8E8F0"
                font.pixelSize: 28
                font.bold: true
                font.family: "Arial"
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            Rectangle {
                Layout.preferredWidth: 300
                Layout.fillHeight: true
                color: "#16213E"
                radius: 8
                border.color: "#0F3460"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: "📦 パーツ庫"
                        color: "#E8E8F0"
                        font.pixelSize: 20
                        font.bold: true
                    }

                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: parts
                        spacing: 6

                        delegate: Rectangle {
                            width: ListView.view.width
                            height: 56
                            color: "#1A1A2E"
                            radius: 6
                            border.color: modelData.color
                            border.width: 2

                            MouseArea {
                                anchors.fill: parent
                                onClicked: equip(modelData)
                            }

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 2

                                Text {
                                    text: modelData.name + " [" + modelData.rank + "]"
                                    color: modelData.color
                                    font.pixelSize: 16
                                    font.bold: true
                                }
                                Text {
                                    text: modelData.slot + " / WT:" + modelData.weight
                                    color: "#8888AA"
                                    font.pixelSize: 12
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#16213E"
                radius: 8
                border.color: "#533483"
                border.width: 2

                GridLayout {
                    anchors.centerIn: parent
                    columns: 2
                    rowSpacing: 16
                    columnSpacing: 16

                    Repeater {
                        model: ["HEAD", "CORE", "R-ARM", "L-ARM", "LEGS", "BOOSTER"]

                        Rectangle {
                            width: 180
                            height: 100
                            color: equipped[modelData] ? "#0F3460" : "#1A1A2E"
                            radius: 8
                            border.color: equipped[modelData] ? equipped[modelData].color : "#555577"
                            border.width: equipped[modelData] ? 3 : 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 4

                                Text {
                                    text: modelData
                                    color: "#8888AA"
                                    font.pixelSize: 14
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Text {
                                    text: equipped[modelData] ? equipped[modelData].name : "EMPTY"
                                    color: equipped[modelData] ? equipped[modelData].color : "#555577"
                                    font.pixelSize: 16
                                    font.bold: true
                                    Layout.alignment: Qt.AlignHCenter
                                    wrapMode: Text.Wrap
                                    Layout.fillWidth: true
                                }
                                Text {
                                    text: equipped[modelData] ? "WT:" + equipped[modelData].weight : ""
                                    color: "#8888AA"
                                    font.pixelSize: 12
                                    Layout.alignment: Qt.AlignHCenter
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.preferredWidth: 260
                Layout.fillHeight: true
                color: "#16213E"
                radius: 8
                border.color: "#0F3460"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    Text {
                        text: "⚡ 機体ステータス"
                        color: "#E8E8F0"
                        font.pixelSize: 20
                        font.bold: true
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 2
                        color: "#533483"
                    }

                    Repeater {
                        model: [
                            { label: "ATK", value: totalStat("atk"), color: "#e74c3c" },
                            { label: "DEF", value: totalStat("def"), color: "#3498db" },
                            { label: "SPD", value: totalStat("spd"), color: "#2ecc71" },
                            { label: "EN", value: totalStat("en"), color: "#f1c40f" },
                            { label: "WEIGHT", value: totalWeight() + " / " + loadLimit(), color: totalWeight() > loadLimit() ? "#e74c3c" : "#E8E8F0" }
                        ]

                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: modelData.label; color: "#8888AA"; font.pixelSize: 16; Layout.preferredWidth: 80 }
                            Text { text: modelData.value; color: modelData.color; font.pixelSize: 18; font.bold: true }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 2
                        color: "#533483"
                    }

                    Text {
                        text: "🔗 シナジー"
                        color: "#E8E8F0"
                        font.pixelSize: 16
                        font.bold: true
                    }
                    Text {
                        text: synergy()
                        color: "#ff00ff"
                        font.pixelSize: 14
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
            }
        }
    }
}
