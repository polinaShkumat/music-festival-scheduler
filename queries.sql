-- Example queries for music_festival.db

-- 1. Where and when does a specific artist perform?
SELECT Stages.name, Performances.date, Performances.start_time
FROM Performances
JOIN Artists ON Performances.artist_id = Artists.artist_id
JOIN Stages ON Performances.stage_id = Stages.stage_id
WHERE Artists.name = 'Artist 7';

-- 2. On which days can you see a rock artist?
SELECT DISTINCT Performances.date
FROM Performances
JOIN Artists ON Performances.artist_id = Artists.artist_id
WHERE Artists.genre = 'Rock'
ORDER BY Performances.date;

-- 3. How many visitors have Artist 12 as a favourite? (many-to-many via the junction table)
SELECT COUNT(*) AS fans
FROM FavoriteArtists
JOIN Artists ON FavoriteArtists.artist_id = Artists.artist_id
WHERE Artists.name = 'Artist 12';

-- 4. Most popular artists by number of fans
SELECT Artists.name, Artists.genre, COUNT(FavoriteArtists.visitor_id) AS fans
FROM Artists
LEFT JOIN FavoriteArtists ON FavoriteArtists.artist_id = Artists.artist_id
GROUP BY Artists.artist_id
ORDER BY fans DESC
LIMIT 5;
