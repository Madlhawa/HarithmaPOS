SELECT s.relname AS sequence_name 
FROM pg_class s 
JOIN pg_depend d 
	ON d.objid = s.oid 
JOIN pg_class t 
	ON d.refobjid = t.oid 
JOIN pg_attribute a 
	ON a.attnum = d.refobjsubid 
	AND a.attrelid = t.oid 
WHERE t.relname = 'customer' 
	AND a.attname = 'id';
	
SELECT currval('customer_id_seq');

SELECT last_value, is_called 
FROM customer_id_seq;

CREATE DATABASE "harithma-db-np";


INSERT INTO public.customer
(id, "name", contact, address, email, create_dttm, update_dttm)
VALUES(1, 'Mandora', '777777777', '', 'Mandora@gmail.com', '2025-01-04 14:32:26.063', '2025-01-04 14:32:26.063');

INSERT INTO public.vehicle
(id, "number", make, model, "year", create_dttm, update_dttm, owner_id)
VALUES(1, 'BAN-5237', 'Nissan', 'Camry', '2020', '2025-01-04 14:32:48.542', '2025-01-04 14:32:48.542', 1);

INSERT INTO public.item
(id, "name", description, unit_of_measure, quantity, unit_cost, unit_price, discount_pct, create_dttm, update_dttm)
VALUES(1, 'Gasoline', '', 'litre', 10.0000, 200.00, 220.00, 0.00, '2025-01-04 14:31:55.966', '2025-01-04 14:31:55.966');

INSERT INTO public.employee
(id, "name", contact, address, designation, joined_date, wage, create_dttm, update_dttm)
VALUES(1, 'Derik', '777777777', 'Akaragama', 'Washer', '2025-01-01', 2200.00, '2025-01-04 14:34:47.103', '2025-01-04 14:34:47.103');

INSERT INTO public.wash_bay
(id, "name", remarks, capacity, create_dttm)
VALUES(1, 'Heavy Jack', 'Jack for heavy vehicles', 10.00, '2025-01-04 14:35:20.113');

INSERT INTO public."user"
(id, email, "name", image, "password", ui_theme, create_dttm, update_dttm)
VALUES(1, 'madhawa242@gmail.com', 'Mandora', 'default.jpg', '$2b$12$LBjZdlDJN2al2.5zyuQqRedCbYKMFkCBxvtYD2OoDYhP0k4Oa1f3C', 'dark', '2025-01-04 14:30:16.787', '2025-01-04 14:30:16.787');