#!/bin/sh

do_tests() {
    just rebuild 2>/dev/null 1>/dev/null
    nosetests3 2>&1 | sort
}

do_tests > before
echo "Make your change and press Enter..."
read _
do_tests > after
colordiff -u before after
rm before after
