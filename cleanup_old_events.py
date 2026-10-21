from event_schedule.routes import delete_old_events
from oshikatsu.oshi_r2 import cleanup_oshi_photos

if __name__ == "__main__":
    delete_old_events()
    print("古いイベントの削除処理が完了しました")

    result = cleanup_oshi_photos()

    print(
        f"推し活日記の写真整理が完了しました "
        f"削除待ち: {result['queued_deleted']}件、"
        f"孤立画像: {result['orphan_deleted']}件"
    )
