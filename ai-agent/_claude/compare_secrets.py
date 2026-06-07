"""Compare AppSecret from file vs expected."""

# Read from .env file directly
with open('.env', 'r') as f:
    lines = f.readlines()
    
secret_line = None
for line in lines:
    if line.startswith('KIS_APP_SECRET='):
        secret_line = line.strip()
        break

if secret_line:
    file_secret = secret_line.split('=', 1)[1]
    print(f"From .env file: {len(file_secret)} chars")
    print(f"Value: {file_secret[:50]}...{file_secret[-50:]}")
else:
    print("Not found in .env")

print()

expected = "d5UVrY6J0EnF3w0/K4gd22gs5VmSOvrNB1vkXVp8RSlu4LW2d1oZvLYYB7cHshNhinQrvC4uBggOwejuPMnbS9uuBNbHSI0QfAkj88CjXss12kVwxPt8dOHFx9Fywo6VhFu9yqICSAlukQ3OcuKr2Ui/44YKzj71jw+W7R2jo/Mx6Sj9oU8="
print(f"Expected: {len(expected)} chars")
print(f"Value: {expected[:50]}...{expected[-50:]}")

print()
print(f"Match: {file_secret == expected if secret_line else False}")

if secret_line and file_secret != expected:
    print("\nFinding differences...")
    min_len = min(len(file_secret), len(expected))
    for i in range(min_len):
        if file_secret[i] != expected[i]:
            print(f"First diff at position {i}:")
            print(f"  File:     '{file_secret[max(0,i-5):i+15]}'")
            print(f"  Expected: '{expected[max(0,i-5):i+15]}'")
            break
