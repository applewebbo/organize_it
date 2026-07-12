def get_trip_stages(trip):
    """
    Return destination stages for a trip.
    Main stage (trip.destination) always first; custom stages follow.
    Each stage: {"destination": str, "days": [Day, ...], "is_main": bool}
    Days with blank destination are treated as belonging to the main stage.
    """
    days = list(trip.days.order_by("number"))
    main_dest = trip.destination
    groups = {}
    for day in days:
        key = day.destination if day.destination else main_dest
        groups.setdefault(key, []).append(day)

    main_days = groups.pop(main_dest, None)
    result = []
    for dest, dest_days in groups.items():
        result.append({"destination": dest, "days": dest_days, "is_main": False})
    if main_days is not None:
        result.append({"destination": main_dest, "days": main_days, "is_main": True})
    elif not result:
        result.append({"destination": main_dest, "days": [], "is_main": True})
    result.sort(key=lambda s: s["days"][0].date if s["days"] else trip.start_date)
    return result


def group_unpaired_events_by_stage(stages, unpaired_events):
    """
    Group unpaired events by stage destination.
    Returns list of dicts: [{"destination": str|None, "events": [...], "is_main": bool}]
    Events whose city matches no stage go into a None-destination group.
    Only groups with at least one event are returned.
    """
    events_list = list(unpaired_events)
    stage_dests = {s["destination"] for s in stages}
    groups = []
    for stage in stages:
        stage_events = [e for e in events_list if e.city == stage["destination"]]
        if stage_events:
            groups.append(
                {
                    "destination": stage["destination"],
                    "events": stage_events,
                    "is_main": stage["is_main"],
                }
            )
    no_stage_events = [
        e for e in events_list if not e.city or e.city not in stage_dests
    ]
    if no_stage_events:
        groups.append(
            {"destination": None, "events": no_stage_events, "is_main": False}
        )
    return groups


def group_days_by_destination(days):
    """
    Group an ordered list of Day objects into consecutive destination blocks.
    Returns a list of dicts:
      [{"destination": str, "days": [Day, ...],
        "next_destination": str|None,
        "transfer_duration": int|None,
        "transfer_distance": int|None}, ...]
    Returns None if all days share the same destination (flat layout).
    """
    day_list = list(days)
    if not day_list:
        return None
    destinations = {d.destination for d in day_list}
    if len(destinations) <= 1:
        return None
    groups = []
    for day in day_list:
        if groups and groups[-1]["destination"] == day.destination:
            groups[-1]["days"].append(day)
        else:
            groups.append({"destination": day.destination, "days": [day]})

    for i, group in enumerate(groups):
        if i < len(groups) - 1:
            next_group = groups[i + 1]
            first_day_of_next = next_group["days"][0]
            group["next_destination"] = next_group["destination"]
            group["transfer_duration"] = first_day_of_next.transfer_duration_from_prev
            group["transfer_distance"] = first_day_of_next.transfer_distance_from_prev
            group["last_day_pk"] = first_day_of_next.pk
        else:
            group["next_destination"] = None
            group["transfer_duration"] = None
            group["transfer_distance"] = None
            group["last_day_pk"] = None
    return groups
