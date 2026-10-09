from event_schedule.routes import delete_old_events


if __name__ == "__main__":
    delete_old_events()
    print("古いイベントの削除処理が完了しました")
