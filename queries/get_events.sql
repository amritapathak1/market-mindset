with base as (
	select
		e.id ,
		e.participant_id ,
		e.event_type ,
		e.event_category ,
		e.page_name ,
		e.task_id ,
		e.element_id ,
		e.element_type ,
		e."action" ,
		e.new_value ,
		e.stock_ticker ,
		e.metadata ,
		e."timestamp"
	from events e
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
	) tbl on tbl.participant_id = e.participant_id
),
task_stocks as (
	select participant_id, task_id, stock_ticker
	from base
	where event_type = 'task_submit'
)
select
	b.id,
	b.participant_id,
	b.event_type,
	b.event_category,
	case
		when b.stock_ticker = 'TUT1' and b.page_name = 'task' then 'tutorial_1'
		when b.stock_ticker = 'TUT2' and b.page_name = 'task' then 'tutorial_2'
		else b.page_name
	end as page_name,
	case
		when b.page_name in ('tutorial_1', 'tutorial_2') or b.stock_ticker in ('TUT1', 'TUT2') then null
		else coalesce(b.task_id, (b.metadata->>'completed_after_task')::int)
	end as task_id,
	b.element_id,
	b.element_type,
	b."action",
	b.new_value,
	case
		when b.page_name = 'tutorial_1' or b.stock_ticker = 'TUT1' then 'TUT1'
		when b.page_name = 'tutorial_2' or b.stock_ticker = 'TUT2' then 'TUT2'
		else coalesce(b.stock_ticker, ts.stock_ticker)
	end as stock_ticker,
	b.metadata,
	b."timestamp"
from base b
left join task_stocks ts
	on ts.participant_id = b.participant_id
	and ts.task_id = coalesce(b.task_id, (b.metadata->>'completed_after_task')::int)
	and b.stock_ticker is null
order by b."timestamp";
