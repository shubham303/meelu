from src.sites.host import read_host


def test_a_www_host_is_kept_not_stripped_to_the_bare_domain():
    assert read_host("www.example.com") == "www.example.com"


def test_a_bare_host_stays_bare():
    assert read_host("example.com") == "example.com"


def test_the_two_host_forms_are_different_values():
    assert read_host("www.example.com") != read_host("example.com")


def test_a_pasted_url_is_reduced_to_its_host_with_www_intact():
    assert read_host("https://www.example.com/pricing?a=1#top") == "www.example.com"
    assert read_host("http://example.com/") == "example.com"


def test_case_and_surrounding_space_are_cleaned_up():
    assert read_host("  WWW.Example.COM  ") == "www.example.com"


def test_a_subdomain_that_is_not_www_is_kept_as_typed():
    assert read_host("blog.example.com") == "blog.example.com"


def test_something_with_no_dot_is_refused():
    assert read_host("localhost") is None


def test_empty_input_is_refused():
    assert read_host("   ") is None


def test_a_host_with_a_space_is_refused_rather_than_truncated():
    assert read_host("exa mple.com") is None
