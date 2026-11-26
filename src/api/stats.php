<?php
// Views, hearts and copies for every market item, kept in one JSON file next to this
// script (data/stats.json, never served: see data/.htaccess). No database, no IP stored:
// a visitor is a random cookie, kept only as a salted hash.
//
//   GET  /api/stats.php                          {"items": {"theme:aequalyn": {"v":1,"h":0,"c":0}, ...}}
//   POST /api/stats.php {"key":"theme:aequalyn","act":"view|heart|unheart|copy"}
//   POST /api/stats.php {"key":"theme:aequalyn","act":"rate","stars":1..5}   (0 takes the rating back)
//                                                {"item": {"v":..,"h":..,"c":..,"r":4.5,"n":2,"d":[0,0,0,1,1],"mine":bool,"my":0..5}}
// One rating per visitor and item, changed at will; "r" is the plain average, "d" the count at 1..5 stars.

declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

const DATA = __DIR__ . '/data';
const STORE = DATA . '/stats.json';
const CATALOG = __DIR__ . '/../data/catalog.json';
const RATE_PER_MINUTE = 60;      // writes one visitor may make in a minute
const COPIES_PER_DAY = 5;        // copies of one item counted for one visitor in a day

function out(int $code, array $body): void {
    http_response_code($code);
    echo json_encode($body, JSON_UNESCAPED_SLASHES);
    exit;
}

function salt(): string {
    $f = DATA . '/salt.txt';
    if (!is_file($f)) {
        @mkdir(DATA, 0750, true);
        file_put_contents($f, bin2hex(random_bytes(32)), LOCK_EX);
        @chmod($f, 0640);
    }
    return trim((string) file_get_contents($f));
}

// The visitor: a random id in a first-party cookie, stored only as a hash.
function visitor(): string {
    $id = $_COOKIE['aev'] ?? '';
    if (!preg_match('/^[0-9a-f]{32}$/', $id)) {
        $id = bin2hex(random_bytes(16));
        $https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || ($_SERVER['SERVER_PORT'] ?? '') == 443;
        setcookie('aev', $id, ['expires' => time() + 31536000, 'path' => '/', 'secure' => $https, 'httponly' => true, 'samesite' => 'Lax']);
    }
    return substr(hash('sha256', salt() . $id), 0, 24);
}

function known_keys(): array {
    static $keys = null;
    if ($keys === null) {
        $keys = [];
        $cat = json_decode((string) @file_get_contents(CATALOG), true);
        foreach (($cat['items'] ?? []) as $it) if (isset($it['key'])) $keys[$it['key']] = true;
    }
    return $keys;
}

// Read, change and write the store under one exclusive lock.
function with_store(callable $fn): mixed {
    @mkdir(DATA, 0750, true);
    $fh = fopen(STORE, 'c+');
    if (!$fh) out(500, ['error' => 'store']);
    flock($fh, LOCK_EX);
    $raw = stream_get_contents($fh);
    $db = $raw ? json_decode($raw, true) : null;
    if (!is_array($db)) $db = [];
    $db += ['items' => [], 'hearts' => [], 'ratings' => [], 'day' => '', 'seen' => [], 'copies' => [], 'minute' => 0, 'rate' => []];
    $result = $fn($db);
    ftruncate($fh, 0);
    rewind($fh);
    fwrite($fh, json_encode($db, JSON_UNESCAPED_SLASHES));
    fflush($fh);
    flock($fh, LOCK_UN);
    fclose($fh);
    return $result;
}

function counts(array $db, string $key): array {
    $c = $db['items'][$key] ?? [];
    return ['v' => (int) ($c['v'] ?? 0), 'h' => (int) ($c['h'] ?? 0), 'c' => (int) ($c['c'] ?? 0)] + rating($db, $key);
}

function rating(array $db, string $key): array {
    $d = [0, 0, 0, 0, 0];
    foreach (($db['ratings'][$key] ?? []) as $s) if ($s >= 1 && $s <= 5) $d[$s - 1]++;
    $n = array_sum($d);
    $sum = 0; foreach ($d as $i => $k) $sum += ($i + 1) * $k;
    return ['r' => $n ? round($sum / $n, 2) : 0, 'n' => $n, 'd' => $d];
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($method === 'GET') {
    $raw = @file_get_contents(STORE);
    $db = $raw ? json_decode($raw, true) : [];
    $items = [];
    $db = is_array($db) ? $db : [];
    foreach (array_unique(array_merge(array_keys($db['items'] ?? []), array_keys($db['ratings'] ?? []))) as $k) {
        $c = counts($db, (string) $k);
        unset($c['d']);
        $items[$k] = $c;
    }
    out(200, ['items' => (object) $items]);
}

if ($method !== 'POST') out(405, ['error' => 'method']);

// Only this site may write (a browser sends Origin on a POST).
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
$host = $_SERVER['HTTP_HOST'] ?? '';
if ($origin !== '' && parse_url($origin, PHP_URL_HOST) !== preg_replace('/:\d+$/', '', $host)) out(403, ['error' => 'origin']);

$in = json_decode((string) file_get_contents('php://input', false, null, 0, 2048), true);
$key = is_array($in) ? (string) ($in['key'] ?? '') : '';
$act = is_array($in) ? (string) ($in['act'] ?? '') : '';
if (!preg_match('/^(plugin|theme|wallpaper|app|cursor|look):[a-z0-9][a-z0-9._-]{0,79}$/', $key)) out(400, ['error' => 'key']);
if (!in_array($act, ['view', 'heart', 'unheart', 'copy', 'rate'], true)) out(400, ['error' => 'act']);
$stars = is_array($in) && isset($in['stars']) && is_int($in['stars']) ? $in['stars'] : -1;
if ($act === 'rate' && ($stars < 0 || $stars > 5)) out(400, ['error' => 'stars']);
if (!isset(known_keys()[$key])) out(404, ['error' => 'unknown']);

$who = visitor();

$item = with_store(function (array &$db) use ($key, $act, $who, $stars) {
    $today = gmdate('Y-m-d');
    if ($db['day'] !== $today) { $db['day'] = $today; $db['seen'] = []; $db['copies'] = []; }
    $minute = intdiv(time(), 60);
    if ($db['minute'] !== $minute) { $db['minute'] = $minute; $db['rate'] = []; }
    $db['rate'][$who] = ($db['rate'][$who] ?? 0) + 1;
    $limited = $db['rate'][$who] > RATE_PER_MINUTE;

    $c = counts($db, $key);
    $hearts = $db['hearts'][$key] ?? [];
    $mine = in_array($who, $hearts, true);

    if (!$limited) {
        $tag = substr(hash('sha256', $who . $key), 0, 16);
        if ($act === 'view' && empty($db['seen'][$tag])) { $db['seen'][$tag] = 1; $c['v']++; }
        if ($act === 'copy' && ($db['copies'][$tag] ?? 0) < COPIES_PER_DAY) { $db['copies'][$tag] = ($db['copies'][$tag] ?? 0) + 1; $c['c']++; }
        if ($act === 'heart' && !$mine) { $hearts[] = $who; $mine = true; }
        if ($act === 'unheart' && $mine) { $hearts = array_values(array_diff($hearts, [$who])); $mine = false; }
        $c['h'] = count($hearts);
        if ($hearts) $db['hearts'][$key] = $hearts; else unset($db['hearts'][$key]);
        if ($act === 'rate') {
            if ($stars === 0) unset($db['ratings'][$key][$who]); else $db['ratings'][$key][$who] = $stars;
            if (empty($db['ratings'][$key])) unset($db['ratings'][$key]);
        }
        $db['items'][$key] = ['v' => $c['v'], 'h' => $c['h'], 'c' => $c['c']];
    }
    return counts($db, $key) + ['mine' => $mine, 'my' => (int) ($db['ratings'][$key][$who] ?? 0)];
});

out(200, ['item' => $item]);
