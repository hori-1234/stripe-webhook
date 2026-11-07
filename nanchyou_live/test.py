from flask import Blueprint, render_template_string

camera_test_bp = Blueprint("camera_test", __name__)

@camera_test_bp.route("/camera-test")
def camera_test():
    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YY併用カメラテスト</title>
    <style>
        body {
            margin: 0;
            padding: 16px;
            background: #111;
            color: white;
            font-family: sans-serif;
            text-align: center;
        }
        video {
            width: 100%;
            max-width: 720px;
            background: black;
        }
        button {
            padding: 12px 24px;
            font-size: 18px;
            margin: 12px;
        }
    </style>
</head>
<body>
    <h2>YY併用カメラテスト</h2>
    <button id="start">カメラON</button>
    <button id="stop">カメラOFF</button>
    <video id="camera" autoplay playsinline muted></video>

    <script>
        let stream = null;
        const video = document.getElementById("camera");

        document.getElementById("start").onclick = async () => {
            try {
                if (stream) return;

                stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: "user" },
                    audio: false
                });

                video.srcObject = stream;
                await video.play();
            } catch (error) {
                alert("カメラ起動エラー: " + error.message);
            }
        };

        document.getElementById("stop").onclick = () => {
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
                stream = null;
            }
            video.srcObject = null;
        };
    </script>
</body>
</html>
    """)

if __name__ == "__main__":
    app.run(debug=True)
