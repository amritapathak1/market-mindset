select f.* from feedback f
join (
	select p.*
	from participants p
	where (
		(
			p.experiment_key = 'e1'
			and p.created_at > '2026-04-20 14:00:00'
			and p.created_at < '2026-04-20 15:45:00'
		)
		or
		(	
			p.experiment_key = 'e6'
			and (
				(p.created_at > '2026-04-20 23:10:00' and p.created_at < '2026-04-20 23:25:00') or
				(p.created_at > '2026-04-21 03:00:00' and p.created_at < '2026-04-21 03:10:00') or
				(p.created_at > '2026-04-21 16:45:00' and p.created_at < '2026-04-21 17:12:00') or
				(p.created_at > '2026-04-21 20:50:00' and p.created_at < '2026-04-21 22:55:00')
			)
		)
		or
		(
			p.experiment_key = 'e5'
			and (
				(p.created_at > '2026-04-22 16:40:00' and p.created_at < '2026-04-22 17:00:00') or
				(p.created_at > '2026-04-22 17:35:00' and p.created_at < '2026-04-22 18:00:00')
			)
		)
		or
		(
			p.experiment_key in ('e2', 'e3', 'e4')
			and p.created_at > '2026-04-22 20:15:00'
			and p.created_at < '2026-04-22 22:50:00'
		)
	) and extract(epoch from (p.last_active - p.created_at)) >= 1
) tbl on tbl.participant_id = f.participant_id 
order by f.submitted_at;