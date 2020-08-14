from PIL import ImageTk
import PIL.Image
import numpy as np
import math
from fontTools.ttLib import TTFont
from xml.dom import minidom
from tkinter import *
import cv2
from os import path
import os
from numba import jit
currentFont = 'Windsong'
@jit(nopython=True)
def validVerticalIntersection(grid, x, y, maxY):
    hasLeft = False
    hasRight = False
    for y in range(max(0, y-50), min(y+50, maxY)):
        if grid[x+1, y][0] == 0:
            hasRight = True
        if grid[x-1, y][0] == 0:
            hasLeft = True
        if hasLeft and hasRight:
            return True
    print(x)
    return False
@jit(nopython=True)
def validHorizontalIntersection(grid, x, y, maxX):
    hasUpper = False
    hasLower = False
    for x in range(max(0, x-50), min(x+50, maxX)):
        if grid[x, y+1][0] == 0:
            hasUpper = True
        if grid[x, y-1][0] == 0:
            hasLower = True
        if hasLower and hasUpper:
            return True
    return False
@jit(nopython=True)
def fillImage(minX, maxX, minY, maxY, data):
    rasterized = data.copy()
    for y in range(minY + 800, 800 + maxY + 3):
        windingNumber = -1
        indices = []
        for z in range(1, maxX - minX + 35):
            if windingNumber == 1:
                indices.append(z)
            if data[z, y][0] == 255 and data[z + 1, y][0] == 0:
                if validHorizontalIntersection(data, z + 1, y, maxX - minX + 36):
                    windingNumber *= -1
        if windingNumber == -1:
            for qr in indices:
                rasterized[qr, y] = [0, 0, 0]
    for x in range(1, maxX - minX + 35):
        windingNumber = -1
        indices = []
        for z in range(minY + 800, 800 + maxY + 3):
            if windingNumber == 1:
                indices.append(z)
            if data[x, z][0] == 255 and data[x, z + 1][0] == 0:
                if validVerticalIntersection(data, x, z + 1, 800 + maxY + 3):
                    windingNumber *= -1
        if windingNumber == -1:
            for qr in indices:
                rasterized[x, qr] = [0, 0, 0]
    return rasterized
@jit(nopython=True)
def antiAlias(minX, maxX, minY, maxY, rasterized):
    rasterizedSampled = rasterized.copy()
    for y in range(minY + 799, 800 + maxY + 2):
        for z in range(1, maxX - minX + 35):
            count = 0
            if rasterized[z - 1, y - 1][0] == 0:
                count += 1
            if rasterized[z - 1, y][0] == 0:
                count += 1
            if rasterized[z - 1, y + 1][0] == 0:
                count += 1
            if rasterized[z, y - 1][0] == 0:
                count += 1
            if rasterized[z, y + 1][0] == 0:
                count += 1
            if rasterized[z + 1, y - 1][0] == 0:
                count += 1
            if rasterized[z + 1, y][0] == 0:
                count += 1
            if rasterized[z + 1, y + 1][0] == 0:
                count += 1
            average = float(1) - float(count / 8)
            averagedColor = int(average * float(255))
            rasterizedSampled[z, y] = [averagedColor, averagedColor, averagedColor]
    return rasterizedSampled
def createText(exampleText):
    font = TTFont(currentFont+'.ttf')
    font.saveXML(currentFont+".ttx")
    rendered = []
    data = np.zeros((80, 2400, 3), dtype=np.uint8)
    data.fill(255)
    space = np.rot90(data, 1, (0, 1))
    rendered.append(space)
    myFont = minidom.parse(currentFont+'.ttx')
    for letter in exampleText:
        stringCode = str(ord(letter))
        if path.exists(currentFont + '-' + stringCode + '.jpg'):
            stored = PIL.Image.open(currentFont + '-' + stringCode + '.jpg')
            stored = np.asarray(stored, dtype=np.uint8)
            rendered.append(stored)
            continue
        if letter == ' ':
            data = np.zeros((700, 2400, 3), dtype=np.uint8)
            data.fill(255)
            space = np.rot90(data, 1, (0, 1))
            rendered.append(space)
            continue
        items = myFont.getElementsByTagName('TTGlyph')
        index = -1
        if letter == '?':
            letter = 'question'
        elif letter == '!':
            letter = 'exclam'
        for x in range(0, len(items)):
            if items[x].attributes['name'].value == letter:
                index = x
                break
        characterGlyph = items[index]
        contour = characterGlyph.getElementsByTagName('contour')
        minX = int(characterGlyph.attributes['xMin'].value)
        minY = int(characterGlyph.attributes['yMin'].value)
        maxX = int(characterGlyph.attributes['xMax'].value)
        maxY = int(characterGlyph.attributes['yMax'].value)
        data = np.zeros((maxX-minX+36, 2400, 3), dtype=np.uint8)
        data.fill(255)
        for p in range(0, len(contour)):
            points = contour.item(p).getElementsByTagName('pt')
            controlPoints = []
            for point in points:
                newPoint = [int(point.attributes['x'].value)-minX+30, int(point.attributes['y'].value)+800, int(point.attributes['on'].value)]
                controlPoints.append(newPoint)
            current = 0
            while current < len(controlPoints):
                if controlPoints[current][2] == 0 and controlPoints[(current+1)%len(controlPoints)][2] == 0:
                    newControlX= 0.5*controlPoints[current][0]+0.5*controlPoints[(current+1)%len(controlPoints)][0]
                    newControlY = 0.5*controlPoints[current][1]+0.5*controlPoints[(current+1)%len(controlPoints)][1]
                    controlPoints = controlPoints[0:current+1]+[[newControlX, newControlY, 1]]+controlPoints[current+1:]
                current+=1
            for z in range(0, len(controlPoints)):
                p1 = controlPoints[z]
                p2 = controlPoints[(z+1)%len(controlPoints)]
                p3 = controlPoints[(z+2)%len(controlPoints)]
                if p1[2]==1 and p2[2] == 1:
                    for x in range(0, 2501):
                        t = x/2500
                        pointX = (1-t)*p1[0]+t*p2[0]
                        pointY = (1-t)*p1[1]+t*p2[1]
                        data[math.floor(pointX), math.floor(pointY)] = [0, 0, 0]
                elif p1[2] == 1 and p3[2] == 1:
                    for x in range(0, 2501):
                        t = x/2500
                        pointX = (1-t)*(1-t)*p1[0]+2*t*(1-t)*p2[0]+t*t*p3[0]
                        pointY = (1-t)*(1-t)*p1[1]+2*t*(1-t)*p2[1]+t*t*p3[1]
                        data[math.floor(pointX), math.floor(pointY)] = [0, 0, 0]
        rasterized = fillImage(minX, maxX, minY, maxY, data)
        rasterizedSampled = antiAlias(minX, maxX, minY, maxY, rasterized)
        corrected = np.rot90(rasterizedSampled, 1, (0, 1))
        rendered.append(corrected)
        cv2.imwrite(currentFont+'-'+stringCode+'.jpg', corrected)
    filler = np.zeros((80, 2400, 3), dtype=np.uint8)
    filler.fill(255)
    space = np.rot90(filler, 1, (0, 1))
    rendered.append(space)
    finalImage = rendered[0]
    for x in range(1, len(rendered)):
        finalImage = np.concatenate((finalImage, rendered[x]), axis=1)
    cv2.imwrite('hconcat.jpg', finalImage)
if __name__ == '__main__':
    window = Tk()
    window.title("Font Rasterizer")
    window.geometry('2000x2500')
    img = None
    def displayControlPoints():
        longtext = ''
        character = showPointsCharacter.get()
        myFont = minidom.parse(currentFont + '.ttx')
        items = myFont.getElementsByTagName('TTGlyph')
        index = -1
        for x in range(0, len(items)):
            if items[x].attributes['name'].value == character:
                index = x
                break
        characterGlyph = items[index]
        contour = characterGlyph.getElementsByTagName('contour')
        for p in range(0, len(contour)):
            longtext = longtext + "Contour "+str(p+1)+": "
            points = contour.item(p).getElementsByTagName('pt')
            for point in points:
                longtext += "("+point.attributes['x'].value +", "+point.attributes['y'].value+ ", onCurve="+point.attributes['on'].value+") "
            longtext+='\n'
        displayPoints.config(text=longtext)
    def changePoint():
        global currentFont
        character = letterToChange.get()
        point = pointToChange.get()
        oldX = point[1:point.index(',')]
        oldY = point[point.index(' ')+1:point.index(')')]
        changeTo = pointToChangeTo.get()
        newX = changeTo[1:changeTo.index(',')]
        changeTo = changeTo[changeTo.index(' ')+1:]
        newY = changeTo[0:changeTo.index(',')]
        changeTo = changeTo[changeTo.index(' ')+1:]
        newOn = changeTo[0]
        print(oldX, oldY)
        print(newX, newY, newOn)
        editFont = minidom.parse(currentFont + '.ttx')
        items = editFont.getElementsByTagName('TTGlyph')
        index = -1
        for x in range(0, len(items)):
            if items[x].attributes['name'].value == character:
                index = x
                break
        characterGlyph = items[index]
        contour = characterGlyph.getElementsByTagName('contour')
        found = False
        for p in range(0, len(contour)):
            points = contour.item(p).getElementsByTagName('pt')
            for point in points:
                print(point.attributes['x'].value)
                foundX = str(point.attributes['x'].value)
                foundY = str(point.attributes['y'].value)
                if foundX == str(oldX) and foundY == str(oldY):
                    print("Success")
                    point.attributes['x'].value=newX
                    point.attributes['y'].value=newY
                    point.attributes['on'].value = newOn
                    found = True
                    break
            if found:
                worked.config(text="Success! Point changed.")
                break
        if not found:
            worked.config(text="Failure: point not found.")
        else:
            with open("myFont.ttx", "w") as fs:
                fs.write(editFont.toxml())
                fs.close()
                customFont = TTFont()
                customFont.importXML('myFont.ttx')
                customFont.save('myFont.ttf')
                currentFont = 'myFont'
                os.remove('myFont-'+str(ord(character))+'.jpg')
    def callback(sv):
        print(sv.get())
        global img
        createText(sv.get())
        image = PIL.Image.open('hconcat.jpg')
        width, height = image.size
        image = image.resize((int(width / 8), int(height / 8)), PIL.Image.ANTIALIAS)
        img = ImageTk.PhotoImage(image)
        lbl1.configure(image=img)
    lbl = Label(window, text="Enter Example Text:")
    lbl.grid(column=0, row=0)
    lbl.grid(sticky=W)
    sv = StringVar()
    sv.trace("w", lambda name, index, mode, sv=sv: callback(sv))
    e = Entry(window, textvariable=sv)
    e.grid(column=1, row=0)
    e.grid(sticky=W)
    lbl1 = Label(window)
    lbl1.grid(row=7)
    edit = Label(window, text="Edit Font")
    edit.grid(column=0, row=2)
    edit.grid(sticky=W)
    changeLetter = Label(window, text="Character to Change:")
    changeLetter.grid(column=0, row=3, sticky=W)
    letterToChange = Entry(window)
    letterToChange.grid(column=1, row=3, sticky=W)
    change = Label(window, text="Point to Change (x, y):")
    change.grid(column=0, row=4, sticky=W)
    pointToChange = Entry(window)
    pointToChange.grid(column=1, row=4, sticky=W)
    update = Label(window, text="(newX, newY, newOnCurve)")
    update.grid(column=0, row=5, sticky=W)
    pointToChangeTo = Entry(window)
    pointToChangeTo.grid(column=1, row=5, sticky=W)
    submit = Button(window, text="Update", command=changePoint)
    submit.grid(column=0, row=6, sticky=W)
    worked = Label(window, text="")
    worked.grid(column=1, row=6, sticky=W)
    showPoints = Label(window, text='Show Control Points for Character:')
    showPoints.grid(column=0, row=8, sticky=W)
    showPointsCharacter = Entry(window)
    showPointsCharacter.grid(column=1, row=8, sticky=W)
    submit2 = Button(window, text="Display Points", command=displayControlPoints)
    submit2.grid(column=0, row=9, sticky=W)
    displayPoints = Label(window, text='', wraplength=1400, anchor=W, justify=LEFT)
    displayPoints.grid(column=0, columnspan=10, row=10, sticky=W)
    window.mainloop()
