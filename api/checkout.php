<?php
// SLOY – tworzy sesję Stripe Checkout z koszyka.
// Serwer sam liczy ceny i dostawę z api/products.json; nie ufa kwotom z przeglądarki.

declare(strict_types=1);
require __DIR__ . '/lib.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    sloy_json(405, ['error' => 'Metoda niedozwolona.']);
}

$in = json_decode(file_get_contents('php://input') ?: '', true);
if (!is_array($in)) {
    sloy_json(400, ['error' => 'Nieprawidłowe dane koszyka.']);
}

$cfg = sloy_config();
$site = rtrim($cfg['site_url'] ?? 'https://sloy.pl', '/');
$slugs = array_values(array_unique(array_filter((array) ($in['cart'] ?? []), 'is_string')));
$ship = (string) ($in['ship'] ?? '');
$country = (string) ($in['country'] ?? 'PL');
$zip = substr(preg_replace('/[^0-9-]/', '', (string) ($in['zip'] ?? '')), 0, 6);
$nip = substr(preg_replace('/\D/', '', (string) ($in['nip'] ?? '')), 0, 10);

if (!$slugs || count($slugs) > 30) {
    sloy_json(400, ['error' => 'Koszyk jest pusty.']);
}

// --- produkty ---------------------------------------------------------------
$catalog = sloy_products();
$sold = sloy_with_store('sold', fn(array &$d) => $d);
$items = [];
foreach ($slugs as $slug) {
    $p = $catalog[$slug] ?? null;
    if (!$p) {
        sloy_json(409, ['error' => 'Jednego z przedmiotów nie ma już w ofercie. Odśwież koszyk.']);
    }
    if ($p['status'] !== 'dostepny' || isset($sold[$slug])) {
        sloy_json(409, ['error' => "„{$p['name']}” został już sprzedany. Usuń go z koszyka."]);
    }
    if (!is_numeric($p['price']) || $p['price'] <= 0) {
        sloy_json(409, ['error' => "Cenę „{$p['name']}” podajemy na zapytanie: napisz na hello@sloy.pl."]);
    }
    $items[$slug] = $p;
}

// --- dostawa (te same zasady co w koszyku na stronie) -------------------------
$sum = fn(array $prices) => round(array_sum($prices), 2);
switch ($ship) {
    case 'pickup':
        $shipName = 'Odbiór osobisty w Krakowie';
        $shipPrice = 0.0;
        break;
    case 'locker':
        $prices = array_column($items, 'inpost');
        if ($country !== 'PL' || in_array(null, $prices, true)) {
            sloy_json(409, ['error' => 'Paczkomat nie jest dostępny dla tego koszyka.']);
        }
        $shipName = count($items) === 1 ? (reset($items)['inpost_label'] ?? 'InPost') : 'InPost';
        $shipPrice = $sum($prices);
        break;
    case 'courier':
        $prices = array_column($items, 'courier');
        if ($country !== 'PL' || in_array(null, $prices, true)) {
            sloy_json(409, ['error' => 'Kurier nie jest dostępny dla tego koszyka.']);
        }
        $shipName = 'Kurier';
        $shipPrice = $sum($prices);
        break;
    default:
        sloy_json(409, ['error' => 'Dowóz mebli wyceniamy indywidualnie: napisz na hello@sloy.pl.']);
}

// --- blokada przedmiotów na czas płatności ------------------------------------
$conflict = sloy_with_store('reservations', function (array &$res) use ($slugs) {
    sloy_prune_reservations($res);
    foreach ($slugs as $s) {
        if (isset($res[$s])) {
            return $s;
        }
    }
    return null;
});
if ($conflict) {
    sloy_json(409, ['error' => "Ktoś właśnie płaci za „{$items[$conflict]['name']}”. Spróbuj ponownie za 30 minut."]);
}

// --- sesja Stripe Checkout ------------------------------------------------------
$expires = time() + 31 * 60; // Stripe wymaga min. 30 minut
$params = [
    'mode' => 'payment',
    'locale' => 'pl',
    'currency' => 'pln',
    'success_url' => $site . '/koszyk/?zamowienie=ok&session_id={CHECKOUT_SESSION_ID}',
    'cancel_url' => $site . '/koszyk/',
    'expires_at' => $expires,
    'customer_creation' => 'always',
    'phone_number_collection' => ['enabled' => 'true'],
    'tax_id_collection' => ['enabled' => 'true'],
    'custom_text' => ['submit' => [
        'message' => "Płacąc, akceptujesz [regulamin sklepu]($site/regulamin/). Przedmiot trzymamy dla Ciebie 30 minut.",
    ]],
    'line_items' => [],
    'shipping_options' => [[
        'shipping_rate_data' => [
            'type' => 'fixed_amount',
            'display_name' => $shipName,
            'fixed_amount' => ['amount' => (int) round($shipPrice * 100), 'currency' => 'pln'],
        ],
    ]],
    'metadata' => [
        'slugs' => implode(',', $slugs),
        'ship' => $ship,
        'nip' => $nip,
    ],
    'payment_intent_data' => [
        'description' => 'SLOY: ' . implode(', ', array_column($items, 'sku')),
    ],
];
foreach ($items as $slug => $p) {
    $product = ['name' => $p['name'], 'metadata' => ['slug' => $slug, 'sku' => (string) $p['sku']]];
    if ($p['sub'] !== '') {
        $product['description'] = $p['sub'];
    }
    if ($p['image']) {
        $product['images'] = [$site . $p['image']];
    }
    $params['line_items'][] = [
        'quantity' => 1,
        'price_data' => [
            'currency' => 'pln',
            'unit_amount' => (int) round($p['price'] * 100),
            'product_data' => $product,
        ],
    ];
}
if ($ship !== 'pickup') {
    $params['shipping_address_collection'] = ['allowed_countries' => ['PL']];
}
if ($ship === 'locker') {
    $params['custom_fields'] = [[
        'key' => 'paczkomat',
        'label' => ['type' => 'custom', 'custom' => 'Kod paczkomatu InPost (np. KRA01M)'],
        'type' => 'text',
        'text' => ['minimum_length' => 5, 'maximum_length' => 12],
    ]];
}

try {
    $session = stripe_request('POST', 'checkout/sessions', $params);
} catch (Throwable $e) {
    sloy_json(502, ['error' => 'Nie udało się otworzyć płatności. Spróbuj ponownie lub napisz na hello@sloy.pl.']);
}

sloy_with_store('reservations', function (array &$res) use ($slugs, $session, $expires) {
    foreach ($slugs as $s) {
        $res[$s] = ['session' => $session['id'], 'expires' => $expires];
    }
});
sloy_log("CHECKOUT {$session['id']} " . implode(',', $slugs) . " ship=$ship");

sloy_json(200, ['url' => $session['url']]);
