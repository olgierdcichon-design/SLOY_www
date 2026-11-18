<?php
// SLOY – odbiera powiadomienia ze Stripe (webhook).
// Opłacone zamówienie: przedmioty trafiają do api/data/sold.json i nie da się ich kupić drugi raz,
// a na adres notify_email idzie e-mail z podsumowaniem. Wygasła płatność: blokada znika.

declare(strict_types=1);
require __DIR__ . '/lib.php';

$payload = file_get_contents('php://input') ?: '';
$header = $_SERVER['HTTP_STRIPE_SIGNATURE'] ?? '';
$secret = sloy_config()['stripe_webhook_secret'] ?? '';

// --- weryfikacja podpisu Stripe ---------------------------------------------
$parts = [];
foreach (explode(',', $header) as $kv) {
    [$k, $v] = array_pad(explode('=', trim($kv), 2), 2, '');
    $parts[$k][] = $v;
}
$t = (int) ($parts['t'][0] ?? 0);
$expected = hash_hmac('sha256', $t . '.' . $payload, $secret);
$valid = false;
foreach ($parts['v1'] ?? [] as $sig) {
    $valid = $valid || hash_equals($expected, $sig);
}
if (!$secret || !$valid || abs(time() - $t) > 300) {
    sloy_json(400, ['error' => 'invalid signature']);
}

$event = json_decode($payload, true);
$type = $event['type'] ?? '';
$s = $event['data']['object'] ?? [];
$slugs = array_filter(explode(',', $s['metadata']['slugs'] ?? ''));

$release = function () use ($slugs, $s) {
    sloy_with_store('reservations', function (array &$res) use ($slugs, $s) {
        foreach ($slugs as $slug) {
            if (($res[$slug]['session'] ?? '') === ($s['id'] ?? '')) {
                unset($res[$slug]);
            }
        }
    });
};

$paid = ($type === 'checkout.session.completed' && ($s['payment_status'] ?? '') === 'paid')
    || $type === 'checkout.session.async_payment_succeeded';

if ($paid) {
    sloy_with_store('sold', function (array &$sold) use ($slugs, $s) {
        foreach ($slugs as $slug) {
            $sold[$slug] = ['session' => $s['id'], 'at' => date('c')];
        }
    });
    $release();
    sloy_notify($s, $slugs);
    sloy_log("PAID {$s['id']} " . implode(',', $slugs));
} elseif (in_array($type, ['checkout.session.expired', 'checkout.session.async_payment_failed'], true)) {
    $release();
    sloy_log(strtoupper(str_replace('checkout.session.', '', $type)) . " {$s['id']}");
}

sloy_json(200, ['received' => true]);

function sloy_notify(array $s, array $slugs): void
{
    $to = sloy_config()['notify_email'] ?? '';
    if (!$to) {
        return;
    }
    $catalog = sloy_products();
    $c = $s['customer_details'] ?? [];
    $addr = $s['shipping_details']['address'] ?? ($s['collected_information']['shipping_details']['address'] ?? []);
    $locker = '';
    foreach ($s['custom_fields'] ?? [] as $f) {
        if (($f['key'] ?? '') === 'paczkomat') {
            $locker = $f['text']['value'] ?? '';
        }
    }
    $lines = array_map(fn($slug) => '- ' . ($catalog[$slug]['name'] ?? $slug) . ' (' . ($catalog[$slug]['sku'] ?? '') . ')', $slugs);
    $taxIds = array_map(fn($x) => $x['value'] ?? '', $c['tax_ids'] ?? []);
    $body = implode("\n", [
        'Nowe opłacone zamówienie w SLOY',
        '',
        'Kwota: ' . number_format(($s['amount_total'] ?? 0) / 100, 2, ',', ' ') . ' zł',
        'Dostawa: ' . ($s['metadata']['ship'] ?? '') . ($locker ? ", paczkomat $locker" : ''),
        '',
        'Przedmioty:',
        ...$lines,
        '',
        'Klient: ' . ($c['name'] ?? '') . ', ' . ($c['email'] ?? '') . ', tel. ' . ($c['phone'] ?? ''),
        'Adres: ' . trim(implode(', ', array_filter([$addr['line1'] ?? '', $addr['line2'] ?? '', ($addr['postal_code'] ?? '') . ' ' . ($addr['city'] ?? '')]))),
        'NIP: ' . trim(($s['metadata']['nip'] ?? '') . ' ' . implode(' ', $taxIds)),
        '',
        'Stripe: https://dashboard.stripe.com/payments/' . ($s['payment_intent'] ?? ''),
        'Pamiętaj: przenieś sprzedane przedmioty do archiwum na stronie.',
    ]);
    $subject = '=?UTF-8?B?' . base64_encode('SLOY: nowe zamówienie ' . number_format(($s['amount_total'] ?? 0) / 100, 0, ',', ' ') . ' zł') . '?=';
    @mail($to, $subject, $body, "Content-Type: text/plain; charset=UTF-8\r\nFrom: SLOY <$to>");
}
