SELECT Continent, COUNT(*) AS num, SUM(c1)
FROM flags
GROUP BY Continent
