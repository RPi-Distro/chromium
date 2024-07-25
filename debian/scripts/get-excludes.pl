#!/usr/bin/perl -w

use strict;

use Dpkg::Control::Hash;

my @exclude_globs = ();
my ($prefix) = @ARGV;
undef $prefix unless ($#ARGV == 0);

if (not defined $prefix) {
	die "usage: $0 <prefix>\n";
}

# This d/copyright code is stolen from Debian's mk-origtargz
my $data = Dpkg::Control::Hash->new();
my $okformat
          = qr'https?://www.debian.org/doc/packaging-manuals/copyright-format/[.\d]+';
eval {
	$data->load("debian/copyright");
	1;
} or do {
	undef $data;
};
if ($data && defined $data->{format} && $data->{format} =~ m@^$okformat/?$@) {
	if ($data->{'Files-Excluded'}) {
		push(@exclude_globs,
                    grep { $_ }
                      split(/\s+/, $data->{'Files-Excluded'}));
	}
};
# end 'borrowed' code

foreach my $line (@exclude_globs) {
	if ($line !~ /^\*/) {
		$line = "${prefix}${line}";
	}
	print STDOUT "$line\n";
}

