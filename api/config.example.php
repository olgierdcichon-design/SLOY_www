<?php
// SLOY – ustawienia płatności.
// 1. Skopiuj ten plik na serwerze (Hostinger) jako api/config.php.
// 2. Wpisz klucze ze Stripe (Developers → API keys oraz Developers → Webhooks).
// 3. NIE wrzucaj config.php do GitHuba ani nie wysyłaj kluczy w czacie.

return [
    // Klucz tajny: sk_test_... (test) albo sk_live_... (prawdziwe płatności)
    'stripe_secret_key' => 'sk_test_WPISZ_TUTAJ',

    // Sekret webhooka: whsec_... (Developers → Webhooks → Twój endpoint → Signing secret)
    'stripe_webhook_secret' => 'whsec_WPISZ_TUTAJ',

    // Adres strony, bez ukośnika na końcu
    'site_url' => 'https://sloy.pl',

    // Na ten adres przyjdzie e-mail o każdym opłaconym zamówieniu
    'notify_email' => 'hello@sloy.pl',
];
