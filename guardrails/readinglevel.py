# Import Guard and Validator
from guardrails import Guard
from guardrails.hub import ReadingLevel

# Create a Guard with the validator
guard = Guard().use(ReadingLevel, min=4, max=8, on_fail="exception")

guard.validate(
    """In a bustling bakery filled with the sweet scent of muffins and cookies, lived a mischievous little yeast named Sprout. 
    Sprout wasn't like the other yeasts who patiently puffed up dough. He longed for adventure! 
    One day, during a mixing frenzy, Sprout jumped on a batch of bread dough and hitched a ride. 
    He soared through the oven, dodging flames like a tiny acrobat, and emerged golden brown and bubbly. 
    Landing on a plate, he saw a wide-eyed boy about to take a bite! Sprout winked,
    "This bread might taste extra bouncy today!" The boy laughed, taking a bite, and his eyes widened 
    with delight. From then on, Sprout continued his bakery escapades, adding a sprinkle of fun to every loaf!
    """
)  # Validator passes

try:
    guard.validate(
        """A Jay venturing into a yard where Peacocks used to walk, found there a number of feathers
        which had fallen from the Peacocks when they were moulting. He tied them all to his tail and strutted
        down towards the Peacocks. When he came near them they soon discovered the cheat, and striding up to him
        pecked at him and plucked away his borrowed plumes. So the Jay could do no better than go back to the
        other Jays, who had watched his behaviour from a distance; but they were equally annoyed with him,
        and told him:"It is not only fine feathers that make fine birds.
        """
    )  # Validator fails
except Exception as e:
    print(e)
