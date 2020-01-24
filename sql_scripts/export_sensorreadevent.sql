SELECT 
	DATE_FORMAT(timestamp, "%Y-%m-%d %H:%i:%s") AS 'data/hora',
   (SELECT sensor_id FROM model_sensor WHERE id = a.sensor_id) AS 'sensor',
   (SELECT 
		(SELECT 
		CASE 
			WHEN prototype_side = 0 
				THEN 'Intensivo' 
			ELSE 'Extensivo' 
		END AS 'lado' 
		FROM model_controlboard
		WHERE id = b.control_board_id)
	FROM model_sensor b 
	WHERE id = a.sensor_id)	AS 'modelo',
	FORMAT(value_read, 2, 'pt_BR') AS 'valor'
FROM model_sensorreadevent a
WHERE 
   sensor_id NOT IN (1, 2, 3, 4, 5, 8, 9, 10, 11, 12) AND 
   timestamp > '2019-09-27 20:35:00' AND
   ((sensor_id IN (7, 15) AND value_read <> 0) OR (sensor_id NOT IN (7, 15)))
ORDER BY timestamp;