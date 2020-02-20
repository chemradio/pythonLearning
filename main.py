import random
f = open('whirlpool.txt')
lottery = f.read().splitlines()
x = random.choice(lottery)
wordList = list(x)
wordLength = len(wordList)
cryptList = []
cryptSign = '*'
i = 0
j = 0
gotcha = 0
attemptsCount = 0
attemptLetters = []
separator = ""

for j in range( wordLength ):
    cryptList.append(cryptSign)

print("Your word length is: " + str(wordLength) + " characters \n" + str( separator.join(cryptList) ) )

suggestedAttemptsCount = int(input("How many attempts? "))

while gotcha < suggestedAttemptsCount:
    
    if attemptsCount == suggestedAttemptsCount:
      print("\nSorry, next time...\n\nThe word was: " + str( separator.join( wordList ) ))
      break

    flagRepeat = 0

    guess = input("\nPick a letter: ")

    for l in attemptLetters:
      if guess == l:
        print("\nCome on! You've already tried that!\n\n" + str( separator.join(cryptList)) ) 
        flagRepeat = 1
        attemptsCount = attemptsCount + 1
        continue

    if flagRepeat == 1:
      continue

    for i in range(wordLength):
      if guess == wordList[i]:
        gotcha = gotcha + 1
        cryptList[i] = wordList[i]
        print("\nGotcha!")
    
    attemptLetters.append(guess)

    print(separator.join(cryptList))
    attemptsCount = attemptsCount + 1
    
    if gotcha == wordLength:
      print('Great job!\nTotal attempts:', attemptsCount)
      break  