<?php
// The contact form: checks the message and mails it to the address in config.php
// (copy config.example.php to config.php on the host; it is never deployed from git).
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function reply(int $code, array $body): void { http_response_code($code); echo json_encode($body); exit; }

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') reply(405, ['error' => 'Use the form, please.']);
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if ($origin !== '' && parse_url($origin, PHP_URL_HOST) !== preg_replace('/:\d+$/', '', $_SERVER['HTTP_HOST'] ?? '')) reply(403, ['error' => 'Not from this site.']);

$cfg = is_file(__DIR__ . '/config.php') ? require __DIR__ . '/config.php' : [];
$to = (string) ($cfg['contact_to'] ?? '');
if (!filter_var($to, FILTER_VALIDATE_EMAIL)) reply(503, ['error' => 'The contact form is not set up yet. Please open an issue on GitHub.']);

// A bot fills the hidden field; a person does not.
if (trim((string) ($_POST['website'] ?? '')) !== '') reply(200, ['ok' => true]);

$name = trim((string) ($_POST['name'] ?? ''));
$email = trim((string) ($_POST['email'] ?? ''));
$msg = trim((string) ($_POST['message'] ?? ''));
if ($name === '' || mb_strlen($name) > 100 || preg_match('/[\r\n]/', $name)) reply(400, ['error' => 'Please give your name.']);
if (!filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($email) > 200) reply(400, ['error' => 'Please give a valid email address.']);
if (mb_strlen($msg) < 5 || mb_strlen($msg) > 5000) reply(400, ['error' => 'Please write a message (up to 5000 characters).']);

// One message a minute from one address, counted by a salted hash (no IP is kept).
$dir = __DIR__ . '/data';
@mkdir($dir, 0750, true);
$salt = is_file("$dir/salt.txt") ? trim((string) file_get_contents("$dir/salt.txt")) : 'aequalyn';
$tag = substr(hash('sha256', $salt . ($_SERVER['REMOTE_ADDR'] ?? '')), 0, 20);
$rf = "$dir/contact-rate.json";
$rate = json_decode((string) @file_get_contents($rf), true) ?: [];
$now = time();
$rate = array_filter($rate, fn($t) => $now - (int) $t < 60);
if (isset($rate[$tag])) reply(429, ['error' => 'One message a minute, please. Try again shortly.']);
$rate[$tag] = $now;
file_put_contents($rf, json_encode($rate), LOCK_EX);

$from = (string) ($cfg['contact_from'] ?? ('no-reply@' . preg_replace('/^www\./', '', preg_replace('/:\d+$/', '', $_SERVER['HTTP_HOST'] ?? 'localhost'))));
$subject = '=?UTF-8?B?' . base64_encode('Aequalyn site: message from ' . $name) . '?=';
$body = "From: $name <$email>\n\n$msg\n";
$headers = implode("\r\n", ["From: Aequalyn site <$from>", "Reply-To: $email", 'Content-Type: text/plain; charset=UTF-8', 'MIME-Version: 1.0']);
if (!@mail($to, $subject, $body, $headers)) reply(500, ['error' => 'It could not be sent. Please try again later, or open an issue on GitHub.']);
reply(200, ['ok' => true]);
