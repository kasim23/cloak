# Template Homebrew formula (update on release)
class Cloak < Formula
  desc "Privacy-first CLI to detect and scrub PII"
  homepage "https://github.com/yourname/cloak"
  url "https://files.pythonhosted.org/packages/.../cloak_privacy-0.1.0.tar.gz"
  sha256 "REPLACE_ME"
  license "MIT"

  depends_on "python@3.12"

  def install
    venv = virtualenv_create(libexec, "python3.12")
    venv.pip_install_and_link buildpath
  end

  test do
    system "#{bin}/cloak", "--help"
  end
end
