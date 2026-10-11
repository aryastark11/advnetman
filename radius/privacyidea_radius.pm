use strict;
use warnings;
use vars qw(%RAD_REQUEST %RAD_REPLY %RAD_CHECK);
use LWP::UserAgent;
use JSON;

# FreeRADIUS return codes
use constant RLM_MODULE_REJECT   => 0;
use constant RLM_MODULE_FAIL     => 1;
use constant RLM_MODULE_OK       => 2;
use constant RLM_MODULE_HANDLED  => 3;
use constant RLM_MODULE_INVALID  => 4;
use constant RLM_MODULE_USERLOCK => 5;
use constant RLM_MODULE_NOTFOUND => 6;
use constant RLM_MODULE_NOOP     => 7;
use constant RLM_MODULE_UPDATED  => 8;

my $PRIVACYIDEA_URL = "http://127.0.0.1:5000/validate/check";

sub authorize {
    $RAD_CHECK{'Auth-Type'} = 'Perl';
    return RLM_MODULE_OK;
}

sub authenticate {
    my $user = $RAD_REQUEST{'User-Name'};
    my $pass = $RAD_REQUEST{'User-Password'};

    if (!$user || !$pass) {
        return RLM_MODULE_REJECT;
    }

    my $ua = LWP::UserAgent->new(timeout => 4);
    my $response = $ua->post($PRIVACYIDEA_URL, [
        user => $user,
        pass => $pass
    ]);

    if ($response->is_success) {
        my $json_text = $response->decoded_content;
        my $data = eval { decode_json($json_text) };
        if ($data && $data->{'result'} && $data->{'result'}->{'value'} == 1) {
            # 2FA Authentication succeeded!
            return RLM_MODULE_OK;
        }
    }

    return RLM_MODULE_REJECT;
}

1;
