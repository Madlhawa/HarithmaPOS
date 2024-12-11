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