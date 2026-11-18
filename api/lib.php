<?php
// SLOY – wspólne funkcje płatności Stripe (Hostinger, PHP 8+, bez Composera).

declare(strict_types=1);
date_default_timezone_set('Europe/Warsaw');

function sloy_config(): array
{
    static $cfg = null;
    if ($cfg === null) {
        $file = __DIR__ . '/config.php';
        if (!is_file($file)) {
            sloy_json(500, ['error' => 'Płatności nie są jeszcze skonfigurowane (brak api/config.php).']);
        }
        $cfg = require $file;
    }
    return $cfg;
}

function sloy_json(int $status, array $data): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function sloy_products(): array
{
    $raw = file_get_contents(__DIR__ . '/products.json');
    return json_decode($raw ?: '{}', true) ?: [];
}

/** Czyta i zapisuje plik JSON z blokadą, żeby dwa zamówienia naraz nie nadpisały danych. */
function sloy_with_store(string $name, callable $fn): mixed
{
    $dir = __DIR__ . '/data';
    if (!is_dir($dir)) {
        mkdir($dir, 0750, true);
    }
    $fh = fopen("$dir/$name.json", 'c+');
    flock($fh, LOCK_EX);
    $data = json_decode(stream_get_contents($fh) ?: '{}', true) ?: [];
    $result = $fn($data);
    ftruncate($fh, 0);
    rewind($fh);
    fwrite($fh, json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    fflush($fh);
    flock($fh, LOCK_UN);
    fclose($fh);
    return $result;
}

function sloy_log(string $line): void
{
    $dir = __DIR__ . '/data';
    if (!is_dir($dir)) {
        mkdir($dir, 0750, true);
    }
    file_put_contents("$dir/orders.log", date('c') . ' ' . $line . "\n", FILE_APPEND | LOCK_EX);
}

function stripe_request(string $method, string $path, array $params = []): array
{
    $key = sloy_config()['stripe_secret_key'] ?? '';
    $ch = curl_init('https://api.stripe.com/v1/' . $path);
    $opts = [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_USERPWD => $key . ':',
        CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_TIMEOUT => 20,
        CURLOPT_HTTPHEADER => ['Stripe-Version: 2024-06-20'],
    ];
    if ($method === 'POST') {
        $opts[CURLOPT_POSTFIELDS] = http_build_query($params);
    }
    curl_setopt_array($ch, $opts);
    $body = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    $data = json_decode((string) $body, true) ?: [];
    if ($code >= 400 || !$data) {
        sloy_log('STRIPE ERROR ' . $code . ' ' . ($data['error']['message'] ?? (string) $body));
        throw new RuntimeException($data['error']['message'] ?? 'Stripe error');
    }
    return $data;
}

/** Usuwa wygasłe blokady (30 min) z listy rezerwacji. */
function sloy_prune_reservations(array &$res): void
{
    $now = time();
    foreach ($res as $slug => $r) {
        if (($r['expires'] ?? 0) < $now) {
            unset($res[$slug]);
        }
    }
}
